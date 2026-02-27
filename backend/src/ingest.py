from module_loading import create_modules, ingester

# Copyright 2024 Florian Kunkel, Miroslav Král, Nina Butz, Simon Dobrick.


def user_input():
    """Choose to create new Topics or Modules and to ingest new Documents."""
    if input("Create new Topic or Module?: [y/n] ") == "y":
        create_modules.create_data()
    if input("Delete Topic? [y/n] ") == "y":
        create_modules.delete_topic()
    if input("Ingest new Documents?: [y/n] ") == "y":
        ingester.ingest()


if __name__ == "__main__":
    ingester.ingest()
