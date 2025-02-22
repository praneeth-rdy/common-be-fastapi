import motor.motor_asyncio

from app.server.config import config

client = motor.motor_asyncio.AsyncIOMotorClient(config.MONGO_URI)

mongo = client.get_database()
