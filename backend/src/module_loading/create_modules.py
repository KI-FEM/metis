import json
import pprint
import shutil
from pathlib import Path
from tkinter import filedialog as fd

current_config = {}
DATA_PATH = Path("../../data/").resolve()


def create_topic():
    """Generates a new directiory in data/ with the name of the topic.

    Progresses into Module creation if the user wants to add modules to the topic.
    """
    topic_name = input("Enter the name of the new topic: ")
    for topic in current_config["topics"]:
        if topic["name"] == topic_name:
            print("The topic already exists.")
            return
    Path.mkdir(DATA_PATH + topic_name)
    new_topic = {"name": topic_name, "modules": []}
    current_config["topics"].append(new_topic)
    intent = input("Add modules to the topic? (y/n)")
    if intent == "y":
        create_module(new_topic)


def create_module(topic=None):
    """Generates new directories in the topic directory for the modules.

    Progresses into submodule creation if the user wants to add submodules to the module
    """
    topic_exists = False
    if topic is None:
        topic = input("Enter the name of the topic: ")
        for t in current_config["topics"]:
            if t["name"] == topic:
                topic_exists = True
                used_topic = t
                break
        if not topic_exists:
            print("The topic does not exist.")
            return
    for t in current_config["topics"]:
        if t == topic or topic_exists:
            topic_exists = True
            used_topic = t
            break
    if not topic_exists:
        print("The topic does not exist.")
        return
    path = DATA_PATH + used_topic["name"] + "/"
    amount_modules = int(input("How many modules do you want to create? "))
    for i in range(amount_modules):
        module_name = input("Enter the name of the new module: ")
        Path.mkdir(path + module_name)
        new_module = {"name": module_name, "submodules": []}
        used_topic["modules"].append(new_module)
        intent = input("Add submodules to the module? (y/n)")
        if intent == "y":
            create_submodules(used_topic["name"], module_name, new_module)


def create_submodules(topic_name, module_name, module=None):
    """Copies Markdown files, in the module directory for the submodules.

    Args:
    ----
    topic_name (str): name of the topic
    module_name (str): name of the module
    module: module object only for internal use

    """
    module_exists = False
    if module is None:
        for topic in current_config["topics"]:
            if topic["name"] == topic_name:
                for mod in topic["modules"]:
                    if mod["name"] == module_name:
                        module = mod
                        module_exists = True
                        break
    else:
        module_exists = True
    if not module_exists:
        print("The module or topic does not exist.")
        return
    current_path = DATA_PATH + topic_name + "/" + module_name + "/"
    print("Please choose the correct Markdown files:")
    filenames = fd.askopenfilenames()
    for file in filenames:
        module["submodules"].append({"name": file.split("/")[-1].split(".")[0]})
        shutil.copy(file, current_path)


def load_config():
    """Loads the structure.json file which acts as a config."""
    file = Path.open("structure.json", "r")
    global current_config
    current_config = json.load(file)
    pprint.pprint(current_config)
    file.close()


def save_config():
    """Saves the current config to the structure.json file."""
    file = Path.open("structure.json", "w")
    file.write(json.dumps(current_config, indent=4))
    file.close()


def delete_topic():
    """Deletes Topic from Config and File system."""
    load_config()
    topic_name = input("Enter the name of the topic you want to delete: ")
    for topic in current_config["topics"]:
        if topic["name"] == topic_name:
            current_config["topics"].remove(topic)
            shutil.rmtree(DATA_PATH + topic_name)
            save_config()
            return
    print("The topic does not exist.")


def create_data():
    """Template method for the program to create new topics, modules or submodules."""
    load_config()
    intent = input("Do you want to create a new topic? (y/n)")
    if intent == "y":
        create_topic()
    else:
        intent = input("Do you want to create a new module? (y/n)")
        if intent == "y":
            create_module()
        else:
            intent = input("Do you want to create a new submodule? (y/n)")
            if intent == "y":
                intent1 = input("For which topic do you want to create a submodule? ")
                intent2 = input("For which module do you want to create a submodule? ")
                create_submodules(intent1, intent2)
    save_config()


if __name__ == "__main__":
    create_data()
