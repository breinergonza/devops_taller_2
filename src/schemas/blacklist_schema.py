"""Schemas Marshmallow para serializacion del modelo Blacklist."""
from flask_marshmallow import Marshmallow

from src.models.blacklist import Blacklist

ma = Marshmallow()


class BlacklistSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Blacklist
        load_instance = True
        include_fk = True


blacklist_schema = BlacklistSchema()
blacklists_schema = BlacklistSchema(many=True)
