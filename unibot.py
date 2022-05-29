import pyautogui
import pynput.mouse
import pyperclip
import time
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from pynput.mouse import Listener
import argparse


def get_parser_args():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--lang",
        default="ru",
        help="Bot language.")

    parser.add_argument(
        "--memory",
        default=5,
        type=int,
        help="How many messages should bot remember.")

    parser.add_argument(
        "--max-mess-len",
        default=1024,
        type=int,
        help="Max message length in symbols.")

    parser.add_argument(
        "--temperature",
        default=0.8,
        type=float,
        help="The more is temperature the more nonsense bot will generate.")

    parser.add_argument(
        "--response",
        default=10.0,
        type=float,
        help="How often bot would check chat and respond in seconds.")

    args = parser.parse_args()
    return args


pos = 0
pos2 = 0
right_pressed = False


def on_click_pos(x, y, button, pressed):  # preparing input/output sources

    global right_pressed
    global pos
    global pos2

    if button == pynput.mouse.Button.right:
        pos = (x, y)
        print(f"Input point was set to {pos}")
        print("Please left click from where bot should get input data")
        right_pressed = True

    elif button == pynput.mouse.Button.left and right_pressed:
        pos2 = (x, y)
        print(f"Output point was set to {pos2}")
        print("Starting the bot...")
        return False


def paste(text: str):  # func for text pasting
    pyperclip.copy(text)
    pyautogui.hotkey("ctrl", "v")


def get_length_param(text: str) -> str:  # input str size in tokens
    tokens_count = len(tokenizer.encode(text))
    if tokens_count <= 15:
        len_param = '1'
    elif tokens_count <= 50:
        len_param = '2'
    elif tokens_count <= 256:
        len_param = '3'
    else:
        len_param = '-'
    return len_param


model_dict = {'ru': 'Grossmend/rudialogpt3_medium_based_on_gpt2',
              'en': 'microsoft/DialoGPT-medium'}

if __name__ == '__main__':

    args = get_parser_args()
    if args.lang not in model_dict.keys():
        raise ValueError('Model language must be "en" or "ru"!')

    print("Loading model weights...")

    tokenizer = AutoTokenizer.from_pretrained(model_dict[args.lang])
    model = AutoModelForCausalLM.from_pretrained(model_dict[args.lang])

    print("Please right click from where bot should get input data")
    with Listener(on_click=on_click_pos) as listener:
        listener.join()

    phrase = ''
    step = 0
    while True:  # main loop

        time.sleep(args.response)


        def copy_clipboard():
            pyautogui.hotkey('ctrl', 'c')
            time.sleep(.01)  # ctrl-c is usually very fast but your program may execute faster
            return pyperclip.paste()


        # double clicks on a position of the cursor
        pyautogui.doubleClick(pos)
        pyautogui.doubleClick(pos)
        pyautogui.doubleClick(pos)

        var = str(copy_clipboard()).strip('\n').strip()
        if var == phrase:  # if current input is the same as latest generated text ignore current iteration
            continue

        # encode the new user input, add parameters and return a tensor in Pytorch
        if args.lang == 'ru':
            new_user_input_ids = tokenizer.encode(
            f"|0|{get_length_param(var)}|" + var + tokenizer.eos_token + "|1|1|", return_tensors="pt")

            # append the new user input tokens to the chat history
            bot_input_ids = torch.cat([chat_history_ids, new_user_input_ids],
                                      dim=-1) if step > 0 else new_user_input_ids

        if args.lang == 'en':
            new_user_input_ids = tokenizer.encode(var + tokenizer.eos_token, return_tensors='pt')

            # append the new user input tokens to the chat history
            bot_input_ids = torch.cat([chat_history_ids, new_user_input_ids],
                                      dim=-1) if step > 0 else new_user_input_ids

        # generated a response
        chat_history_ids = model.generate(
            bot_input_ids,
            num_return_sequences=1,
            max_length=args.max_mess_len,
            no_repeat_ngram_size=3,
            do_sample=True,
            top_k=50,
            top_p=0.9,
            temperature=args.temperature,
            mask_token_id=tokenizer.mask_token_id,
            eos_token_id=tokenizer.eos_token_id,
            unk_token_id=tokenizer.unk_token_id,
            pad_token_id=tokenizer.pad_token_id,
            device='cpu',
        )

        step += 1
        if step >= args.memory:  # reset memory
            step = 0

        # double clicks on a position of the cursor
        pyautogui.doubleClick(pos2)
        pyautogui.doubleClick(pos2)

        gen_text = f'{tokenizer.decode(chat_history_ids[:, bot_input_ids.shape[-1]:][0], skip_special_tokens=True)}'  # generate a response
        print(gen_text)
        phrase = gen_text
        paste(gen_text)
        pyautogui.press('Enter')  # send a response
