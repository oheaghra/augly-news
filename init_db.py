from app import app, db, Article

with app.app_context():
    test_hero = Article(
        rank=0,
        category="Politics",
        headline="AuglyNEWS Database is Live!",
        source="System",
        image_url="https://images.unsplash.com/photo-1504711434969-e33886168f5c?q=80&w=800"
    )
    db.session.add(test_hero)
    db.session.commit()
    print("Database seeded with a Hero article!")