import os
import feedparser
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from functools import wraps
from flask import Response

# --- SIMPLE SECURITY CONFIG ---
ADMIN_USER = "admin"
ADMIN_PASS = "!nimda" # Change this to your preferred password

def check_auth(username, password):
    return username == ADMIN_USER and password == ADMIN_PASS

def authenticate():
    return Response(
    'Could not verify your access level for that URL.\n'
    'You have to login with proper credentials', 401,
    {'WWW-Authenticate': 'Basic realm="Login Required"'})

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

app = Flask(__name__)

# --- Database Configuration ---
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'augly.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

app.config['SECRET_KEY'] = 'a-very-long-and-random-string-12345'

db = SQLAlchemy(app)

# --- MODELS ---

class Feed(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    url = db.Column(db.String(500), unique=True)

class Article(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # Rank: 0=Hero, 1-6=Main, 7+=Secondary, 99=Brief
    rank = db.Column(db.Integer, default=10) 
    category = db.Column(db.String(50))
    headline = db.Column(db.String(200), nullable=False)
    source = db.Column(db.String(100))
    image_url = db.Column(db.String(500))
    external_link = db.Column(db.String(500), index=True)
    body = db.Column(db.Text) # For original content
    date_added = db.Column(db.DateTime, default=datetime.utcnow)

class QuickLink(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    label = db.Column(db.String(100), nullable=False)
    url = db.Column(db.String(500), nullable=False)
    category = db.Column(db.String(100), default="General") # This is your Header
    order = db.Column(db.Integer, default=0) # To sort within the group

# Initialize Database
with app.app_context():
    db.create_all()

# --- ROUTES ---

@app.route('/')
def index():
    # ... (Keep your Article queries as they are) ...
    hero = Article.query.filter_by(rank=0).first()
    main_featured = Article.query.filter(Article.rank >= 1, Article.rank <= 6).order_by(Article.rank).all()
    secondary_featured = Article.query.filter(Article.rank >= 7, Article.rank <= 98).order_by(Article.rank).all()
    briefs = Article.query.filter_by(rank=99).order_by(Article.date_added.desc()).all()

    # 1. Fetch links sorted by their 'order' value
    all_links = QuickLink.query.order_by(QuickLink.order).all()
    
    # 2. Build the dictionary while PRESERVING the order they were fetched in
    from collections import OrderedDict
    grouped_links = OrderedDict()
    
    for link in all_links:
        if link.category not in grouped_links:
            grouped_links[link.category] = []
        grouped_links[link.category].append(link)

    return render_template('index.html', 
                           hero=hero, main_featured=main_featured, 
                           secondary_featured=secondary_featured, briefs=briefs,
                           grouped_links=grouped_links)

@app.route('/admin', methods=['GET', 'POST'])
@requires_auth
def admin():
    if request.method == 'POST':
        if 'link_label' in request.form: # Logic for adding a link
            new_link = QuickLink(
                label=request.form.get('link_label'),
                url=request.form.get('link_url'),
                category=request.form.get('link_category'),
                order=int(request.form.get('link_order') or 0)
            )
            db.session.add(new_link)
        else: # Logic for adding an article (your existing code)
            # ... existing article code ...
            pass
        
        db.session.commit()
        return redirect(url_for('admin'))

    articles = Article.query.order_by(Article.rank).all()
    links = QuickLink.query.order_by(QuickLink.category).all()
    return render_template('admin.html', articles=articles, links=links)

@app.route('/admin/feeds', methods=['GET', 'POST'])
@requires_auth
def manage_feeds():
    if request.method == 'POST':
        new_feed = Feed(name=request.form.get('name'), url=request.form.get('url'))
        db.session.add(new_feed)
        db.session.commit()
        return redirect(url_for('manage_feeds'))
    feeds = Feed.query.all()
    return render_template('manage_feeds.html', feeds=feeds)

@app.route('/sync')
@requires_auth
def sync_feeds():
    feeds = Feed.query.all()
    for f in feeds:
        parsed = feedparser.parse(f.url)
        for entry in parsed.entries[:10]: # Check top 10
            # NEW LOGIC: Check if the LINK exists, not the headline
            exists = Article.query.filter_by(external_link=entry.link).first()
            
            if not exists:
                new_art = Article(
                    headline=entry.title,
                    external_link=entry.link,
                    source=f.name,
                    category="RSS Import",
                    rank=99 
                )
                db.session.add(new_art)
    
    db.session.commit()
    return redirect(url_for('admin'))

# --- ROUTE TO DELETE A LINK ---
@app.route('/delete_link/<int:id>')
@requires_auth
def delete_link(id):
    link = QuickLink.query.get_or_404(id)
    db.session.delete(link)
    db.session.commit()
    return redirect(url_for('admin'))

# --- ROUTE TO UPDATE LINK ORDER/CATEGORY ---
@app.route('/update_link/<int:id>', methods=['POST'])
@requires_auth
def update_link(id):
    link = QuickLink.query.get_or_404(id)
    link.category = request.form.get('category')
    link.order = int(request.form.get('order') or 0)
    link.label = request.form.get('label')
    db.session.commit()
    return redirect(url_for('admin'))

@app.route('/delete/<int:id>')
@requires_auth
def delete(id):
    article_to_delete = Article.query.get_or_404(id)
    db.session.delete(article_to_delete)
    db.session.commit()
    return redirect(url_for('admin'))

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
@requires_auth
def edit_article(id):
    article = Article.query.get_or_404(id)
    if request.method == 'POST':
        article.headline = request.form.get('headline')
        article.rank = int(request.form.get('rank'))
        article.category = request.form.get('category')
        article.source = request.form.get('source')
        article.image_url = request.form.get('image_url')
        article.body = request.form.get('body')
        db.session.commit()
        return redirect(url_for('admin'))
    return render_template('edit.html', article=article)

    # Route to see ALL original articles
@app.route('/originals')
def originals_archive():
    # Only fetch articles where source is 'Original'
    articles = Article.query.filter_by(source='Original').order_by(Article.date_added.desc()).all()
    return render_template('originals_archive.html', articles=articles)

# Route to see a SINGLE original article
@app.route('/article/<int:id>')
def article_detail(id):
    article = Article.query.get_or_404(id)
    return render_template('article_detail.html', article=article)

if __name__ == '__main__':
    app.run(debug=False)