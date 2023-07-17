import pytest
from mongoengine import Document, StringField

from pypepper.helper.db import mongodb


class Animals(Document):
    name = StringField(max_length=128, required=True)
    color = StringField(max_length=32, required=False)
    meta = {'collection': 'animals'}


cat1 = Animals(
    name='cat',
    color='white',
)

cat2 = Animals(
    name='cat',
    color='black',
)

cat3 = Animals(
    name='cat',
    color='yellow',
)

dog1 = Animals(
    name='dog',
    color='pink'
)


def test_connect():
    mongodb.connect(mongodb.Config(
        uri='mongodb://test:test@localhost:27017/test'
    ))
    mongodb.close()


def test_all():
    mongodb.connect(mongodb.Config(
        uri='mongodb://test:test@localhost:27017/test'
    ))

    # Insert
    cat1.save()
    cat2.save()
    cat3.save()
    dog1.save()

    # Count
    count = Animals.objects().count()
    print(f'Count={count}')

    # Query all
    print("Query all...")
    for animal in Animals.objects:
        print(f'[QueryAll] id={animal.id}, name={animal.name}, color={animal.color}')
        if animal.color == 'white':
            print(f"Changing animal({animal.id})'s color from {animal.color} to pink...")
            animal.color = 'pink'
            animal.save()

    # Filter Query
    print("Query 'cat'...")
    cats = Animals.objects(name='cat')
    for cat in cats:
        print(f'[FilterQuery] id={cat.id}, name={cat.name}, color={cat.color}')

    print("Querying 'pink'...")
    pinks = Animals.objects(color='pink')
    for pink in pinks:
        print(f'[FilterQuery] id={pink.id}, name={pink.name}, color={pink.color}')

    # Update
    cat2.color = 'white'
    cat2.save()

    # Delete
    print("Deleting cat1...")
    cat1.delete()
    count = Animals.objects(id=cat1.id).count()
    assert count == 0
    print("cat1 deleted")

    # Filter Delete
    print("Deleting all cats...")
    Animals.objects(name='cat').delete()
    count = Animals.objects(name='cat').count()
    assert count == 0
    print("All cats deleted")

    # Delete all
    print("Deleting all...")
    Animals.objects().delete()
    count = Animals.objects().count()
    print(f'All objects deleted. Count={count}')
    assert count == 0

    # Delete again
    cat3.delete()

    # Close
    mongodb.close()


if __name__ == '__main__':
    pytest.main()
