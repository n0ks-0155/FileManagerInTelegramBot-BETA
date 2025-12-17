from telebot.types import CallbackQuery
from utils.data_manager import load_data, save_data, init_user
from utils.navigation import navigate_to_path
from utils.keyboards import generate_markup
import telebot
import logging

logger = logging.getLogger(__name__)

def register_callback_handlers(bot: telebot.TeleBot):
    @bot.callback_query_handler(func=lambda call: True)
    def handle_callback(call: CallbackQuery):
        user_id = str(call.message.chat.id)
        data = load_data()
        init_user(data, user_id)

        if call.data.startswith("delete_file:") or call.data.startswith("shared_delete_file:") or \
           call.data.startswith("delete_text:") or call.data.startswith("shared_delete_text:"):
            
            is_shared = call.data.startswith("shared_")
            parts = call.data.split(":")
            
            if is_shared:
                #Для публичных файлов: shared_delete_file:ключ:short_id или shared_delete_text:ключ:index
                if len(parts) < 3:
                    bot.answer_callback_query(call.id, "Ошибка в формате запроса.")
                    return
                
                shared_key = parts[1]
                file_identifier = parts[2]
                delete_type = parts[0]  
                
                #Находим владельца папки
                shared_info = data.get("shared_folders", {}).get(shared_key)
                if not shared_info:
                    bot.answer_callback_query(call.id, "Ключ доступа не найден.")
                    return
                
                owner_id = shared_info["user_id"]
                path = shared_info["path"]
                
                try:
                    current = navigate_to_path(data["users"][owner_id]["structure"], path)
                except KeyError:
                    bot.answer_callback_query(call.id, "Папка не найдена.")
                    return
                    
            else:
                owner_id = user_id
                path = data["users"][user_id]["current_path"]
                file_identifier = parts[1]
                delete_type = parts[0]  
                current = navigate_to_path(data["users"][owner_id]["structure"], path)
            
            file_deleted = False
            if delete_type in ["delete_file", "shared_delete_file"]:
                for i, file in enumerate(current["files"]):
                    if file.get("short_id") == file_identifier:
                        if file_identifier in data["users"][owner_id]["file_mappings"]:
                            del data["users"][owner_id]["file_mappings"][file_identifier]
                        current["files"].pop(i)
                        file_deleted = True
                        break
            else:
                try:
                    idx = int(file_identifier)
                    if 0 <= idx < len(current["files"]) and current["files"][idx]["type"] == "text":
                        current["files"].pop(idx)
                        file_deleted = True
                except (ValueError, IndexError):
                    pass
            
            if file_deleted:
                save_data(data)
                bot.answer_callback_query(call.id, "Файл удален.")
                
                if is_shared:
                    markup = generate_markup(current, path, shared_key=shared_key)
                else:
                    markup = generate_markup(current, path)
                
                try:
                    bot.edit_message_reply_markup(
                        chat_id=call.message.chat.id,
                        message_id=call.message.message_id,
                        reply_markup=markup
                    )
                except Exception as e:
                    logger.error(f"Ошибка обновления клавиатуры: {e}")
            else:
                bot.answer_callback_query(call.id, "Файл не найден.")
            
            return

        if call.data == "up":
            if data["users"][user_id]["current_path"]:
                popped = data["users"][user_id]["current_path"].pop()
                bot.answer_callback_query(call.id, f"Вернулись из папки '{popped}'.")
            else:
                bot.answer_callback_query(call.id, "Вы уже в корневой папке.")
        elif call.data.startswith("folder:"):
            folder_name = call.data.split(":", 1)[1]
            current = navigate_to_path(data["users"][user_id]["structure"], data["users"][user_id]["current_path"])
            if folder_name in current["folders"]:
                data["users"][user_id]["current_path"].append(folder_name)
                bot.answer_callback_query(call.id, f"Перешли в папку '{folder_name}'.")
            else:
                bot.answer_callback_query(call.id, "Папка не найдена.")
        elif call.data.startswith("file:") or call.data.startswith("text:") or \
             call.data.startswith("shared_file:") or call.data.startswith("shared_text:"):
            
            is_shared = call.data.startswith("shared_")
            parts = call.data.split(":")
            
            if is_shared:
                #Для публичных файлов
                if len(parts) < 3:
                    bot.answer_callback_query(call.id, "Ошибка в формате запроса.")
                    return
                
                shared_key = parts[1]
                file_identifier = parts[2]
                action_type = parts[0] 
                
                shared_info = data.get("shared_folders", {}).get(shared_key)
                if not shared_info:
                    bot.answer_callback_query(call.id, "Ключ доступа не найден.")
                    return
                
                owner_id = shared_info["user_id"]
                path = shared_info["path"]
                
                #Переходим к папке владельца
                try:
                    current = navigate_to_path(data["users"][owner_id]["structure"], path)
                except KeyError:
                    bot.answer_callback_query(call.id, "Папка не найдена.")
                    return
                    
            else:
                #Для личных файлов
                owner_id = user_id
                path = data["users"][user_id]["current_path"]
                file_identifier = parts[1]
                action_type = parts[0] 
                current = navigate_to_path(data["users"][owner_id]["structure"], path)
            
            file_info = None
            if action_type in ["file", "shared_file"]:
                for file in current["files"]:
                    if file.get("short_id") == file_identifier:
                        file_info = file
                        break
            else:
                try:
                    idx = int(file_identifier)
                    if 0 <= idx < len(current["files"]) and current["files"][idx]["type"] == "text":
                        file_info = current["files"][idx]
                except (ValueError, IndexError):
                    pass
            
            if not file_info:
                bot.answer_callback_query(call.id, "Файл не найден.")
                return
            
            try:
                if file_info["type"] == "text":
                    bot.send_message(call.message.chat.id, file_info["content"])
                elif file_info["type"] == "document":
                    bot.send_document(call.message.chat.id, file_info["file_id"])
                elif file_info["type"] == "photo":
                    bot.send_photo(call.message.chat.id, file_info["file_id"])
                elif file_info["type"] == "video":
                    bot.send_video(call.message.chat.id, file_info["file_id"])
                elif file_info["type"] == "audio":
                    bot.send_audio(call.message.chat.id, file_info["file_id"])
                bot.answer_callback_query(call.id, "Файл отправлен.")
            except Exception as e:
                logger.error(f"Ошибка при отправке файла: {e}")
                bot.answer_callback_query(call.id, f"Ошибка при отправке файла: {str(e)}")
            
            return
        
        elif call.data == "retrieve_all" or call.data.startswith("shared_retrieve_all:"):
            is_shared = call.data.startswith("shared_")
            
            if is_shared:
                shared_key = call.data.split(":")[1]
                shared_info = data.get("shared_folders", {}).get(shared_key)
                if not shared_info:
                    bot.answer_callback_query(call.id, "Ключ доступа не найден.")
                    return
                
                owner_id = shared_info["user_id"]
                path = shared_info["path"]
                try:
                    current = navigate_to_path(data["users"][owner_id]["structure"], path)
                except KeyError:
                    bot.answer_callback_query(call.id, "Папка не найдена.")
                    return
            else:
                owner_id = user_id
                path = data["users"][user_id]["current_path"]
                current = navigate_to_path(data["users"][owner_id]["structure"], path)
            
            try:
                for file in current["files"]:
                    if file["type"] == "text":
                        bot.send_message(call.message.chat.id, f"Текст: {file['content']}")
                    elif file["type"] == "document":
                        bot.send_document(call.message.chat.id, file["file_id"])
                    elif file["type"] == "photo":
                        bot.send_photo(call.message.chat.id, file["file_id"])
                    elif file["type"] == "video":
                        bot.send_video(call.message.chat.id, file["file_id"])
                    elif file["type"] == "audio":
                        bot.send_audio(call.message.chat.id, file["file_id"])
                    else:
                        bot.send_message(call.message.chat.id, "Неизвестный тип файла.")
                bot.answer_callback_query(call.id, "Все файлы отправлены.")
            except Exception as e:
                logger.error(f"Ошибка при отправке файлов: {e}")
                bot.answer_callback_query(call.id, f"Ошибка при отправке файлов: {str(e)}")
            
            return

        elif call.data.startswith("shared_"):
            parts = call.data.split(":")
            if len(parts) < 2:
                bot.answer_callback_query(call.id, "Неверный формат команды.")
                return
            
            action = parts[0]
            shared_key = parts[1]
            
            shared_info = data.get("shared_folders", {}).get(shared_key)
            if not shared_info:
                bot.answer_callback_query(call.id, "Ключ доступа не найден.")
                return
            
            owner_id = shared_info["user_id"]
            path = shared_info["path"]
            
            if action == "shared_up":
                if path:
                    path.pop()
                    shared_info["path"] = path
                    save_data(data)
                    bot.answer_callback_query(call.id, "Вернулись на уровень выше.")
                else:
                    bot.answer_callback_query(call.id, "Вы уже в корневой папке.")
            elif action == "shared_folder":
                if len(parts) < 3:
                    bot.answer_callback_query(call.id, "Не указано имя папки.")
                    return
                
                folder_name = parts[2]
                try:
                    current = navigate_to_path(data["users"][owner_id]["structure"], path)
                    if folder_name in current["folders"]:
                        path.append(folder_name)
                        shared_info["path"] = path
                        save_data(data)
                        bot.answer_callback_query(call.id, f"Перешли в папку '{folder_name}'.")
                    else:
                        bot.answer_callback_query(call.id, "Папка не найдена.")
                except KeyError:
                    bot.answer_callback_query(call.id, "Ошибка навигации.")
            
            try:
                current = navigate_to_path(data["users"][owner_id]["structure"], path)
                markup = generate_markup(current, path, shared_key=shared_key)
                bot.edit_message_reply_markup(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    reply_markup=markup
                )
            except Exception as e:
                logger.error(f"Ошибка обновления клавиатуры: {e}")

        if call.data.startswith("folder:") or call.data == "up":
            current = navigate_to_path(data["users"][user_id]["structure"], data["users"][user_id]["current_path"])
            markup = generate_markup(current, data["users"][user_id]["current_path"])
            try:
                bot.edit_message_reply_markup(chat_id=call.message.chat.id,
                                              message_id=call.message.message_id,
                                              reply_markup=markup)
            except telebot.apihelper.ApiTelegramException as e:
                if "message is not modified" in str(e):
                    pass
                else:
                    logger.error(f"Ошибка обновления клавиатуры: {e}")
                    bot.send_message(call.message.chat.id, f"Ошибка обновления клавиатуры: {str(e)}")

        save_data(data)
