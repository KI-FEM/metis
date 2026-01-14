from module_loading import create_modules, ingester

# This script is used to ingest new documents from the data/ folder into the database.
# original copyright 2024 Florian Kunkel, Miroslav Král, Nina Butz, Simon Dobrick.


def user_input():
    """Choose to create new Topics or Modules and to ingest new Documents."""
    if input("Create new Topic or Module?: [y/n] ") == "y":
        create_modules.create_data()
    if input("Delete Topic? [y/n] ") == "y":
        create_modules.delete_topic()
    if input("Ingest new Documents?: [y/n] ") == "y":
        ingester.ingest()


if __name__ == "__main__":
    import asyncio
    import platform
    
    if platform.system() == 'Windows':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(ingester.ingest())
