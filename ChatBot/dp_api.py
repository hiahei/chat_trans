from openai import OpenAI
import json
import os

client = OpenAI(api_key="sk-93eabe26025e4d909a9b19527ba5337e", base_url="https://api.deepseek.com")

messages = []  # 存储所有对话历史
history_file = "chat_history.json"  # 历史记录存储文件
bot_role = "你是一个会议助手"  # 用户设定的 Bot 要求
welcome_message = "您好！我是您的会议小助手，有什么需要帮助的吗？"  # Bot 的欢迎语

def save_history(messages):
    """将对话历史保存到文件"""
    with open(history_file, "w", encoding="utf-8") as f:
        json.dump(messages, f, ensure_ascii=False, indent=4)

def load_history():
    """从文件加载对话历史"""
    try:
        # 如果文件不存在，创建文件并加入 Bot 要求
        if not os.path.exists(history_file):
            initial_messages = [{"role": "system", "content": bot_role}]
            save_history(initial_messages)
            return initial_messages
        with open(history_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        # 如果文件内容不是合法的 JSON，返回初始化的 Bot 要求
        return [{"role": "system", "content": bot_role}]

def print_history(messages):
    """打印对话历史"""
    if not messages:
        print("当前没有历史记录。")
    else:
        print("===== 历史记录 =====")
        for msg in messages:
            if msg["role"] == "system":  # 不打印系统角色（Bot 要求）
                continue
            print(f"{msg['role'].capitalize()}: {msg['content']}")
        print("===================")

# 程序启动时加载历史记录
messages = load_history()

# 每次启动时都添加欢迎语
messages.append({"role": "assistant", "content": welcome_message})
print(f"Bot: {welcome_message}")

# 打印历史记录
# print_history(messages)

while True:
    user_input = input("你：")  # 让用户输入问题

    if user_input.lower() in ["exit", "quit", "q"]:  # 输入 exit / quit 退出
        break
    elif user_input.lower() == "history":  # 输入 history 查看历史记录
        print_history(messages)
        continue

    messages.append({"role": "user", "content": user_input})  # 记录用户输入

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=messages
    )
    bot_message = response.choices[0].message
    messages.append({"role": "assistant", "content": bot_message.content})  # 记录Bot回复

    print(f"Bot: {bot_message.content}")

    # 保存历史记录
    save_history(messages)