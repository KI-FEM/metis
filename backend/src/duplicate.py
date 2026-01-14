import asyncio

from bot_duplication import duplication

# This script is used to create a new bot by copying an existing one.

if __name__=="__main__":
    import platform

    if platform.system() == "Windows":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(duplication.copy_new_bot())