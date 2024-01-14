from warnings import filterwarnings
filterwarnings("ignore")
import telebot
from pymongo import MongoClient
import math
from threading import Thread
import google.generativeai as genai
from time import sleep

genai.configure("REPLACE WITH GOOGLE API TOKEN")
bot = telebot.TeleBot('TELEGRAM BOT TOKEN')
mongo_client = MongoClient('MONGO DB Token')
db = mongo_client['findmeafriend']
collection = db['users']
notifications_collection = db['notifications']

END_MESSAGE = "Sad to see you go! 😔 If you ever want to connect again, just type /start. Your journey with FindMeAFriend awaits whenever you're ready! 🚀💬"
START, AWAIT_LOCATION, AWAIT_ACTIVITY, AWAIT_END, DATA_CHANGE = range(5)
REFRESH_RATE = 1
TIMEOUT = 900 #15 min auto exit

def correct_activity(activity):
  defaults_activity = {
  'model': 'models/text-bison-001',
  'temperature': 0,
  'candidate_count': 8,
  'top_k': 40,
  'top_p': 1,
  'max_output_tokens': 50,
  'stop_sequences': [],
  }
  prompt = f"""
correct spelling and grammar
convert to a singular noun phrase or to a verb phrase in simple present tense and remove the subject

{activity}

output only
"""
  response = genai.generate_text(
    **defaults_activity,
    prompt=prompt
  )
  return response.result

def check_activity(activity1, activity2):
  defaults = {
  'model': 'models/text-bison-001',
  'temperature': 0,
  'candidate_count': 2,
  'top_k': 3,
  'top_p': 1,
  'max_output_tokens': 3,
  'stop_sequences': [],
  }
  prompt = f"""
{activity1}
{activity2}
are they related and can be done together easily

yes or no


"""
  response = genai.generate_text(
    **defaults,
    prompt=prompt
  )
  return response.result and response.result.lower() == 'yes'

def haversine_distance(lat1, lon1, lat2, lon2):
    radius = 6371000
    lat1 = math.radians(lat1)
    lon1 = math.radians(lon1)
    lat2 = math.radians(lat2)
    lon2 = math.radians(lon2)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance = radius * c
    return distance < 300

def auto_exit(chat_id, collection):
    user = collection.find_one({'id': chat_id})
    if user:
        collection.delete_one({'id': chat_id})
        markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
        button_start = telebot.types.KeyboardButton(text="/start")
        markup.add(button_start)
        user = collection.find_one({'id': chat_id})
        bot.send_message(chat_id, "Oops! ⌛️ Your session has expired, and we've gracefully exited. Feel free to restart your journey anytime with /start. The FindMeAFriend world is always here for you! 🚀💬", reply_markup = markup)
        delete_notifications(chat_id, notifications_collection)

def find_nearby_users_periodic(chat_id, collection):
    i = 0
    while True:
      user = collection.find_one({'id': chat_id})
      if not user:
          return
      elif i >= TIMEOUT:
        auto_exit(chat_id, collection)
        return
      elif user['status'] == AWAIT_END:
          user_latitude = user['latitude']
          user_longitude = user['longitude']
          user_activity = user['activity']
          nearby_users = []
          not_nearby_users = []
          data = notifications_collection.find_one({'chat_id': chat_id})
          for other_user in collection.find({'id': {'$ne': chat_id}, 'status': AWAIT_END}):
              other_data = notifications_collection.find_one({'chat_id': other_user['id']})
              if f"{other_user['first_name']} {other_user['last_name']} {other_user['username']}" in data['message']:
                nearby_users.append(f"{other_user['first_name']} {other_user['last_name']} {other_user['username']}")
              elif f"{other_user['first_name']} {other_user['last_name']} {other_user['username']}" in data['not_message']:
                  not_nearby_users.append(f"{other_user['first_name']} {other_user['last_name']} {other_user['username']}")
              elif haversine_distance(user_latitude, user_longitude, other_user['latitude'], other_user['longitude']) and check_activity(user_activity, other_user['activity']):
                  nearby_users.append(f"{other_user['first_name']} {other_user['last_name']} {other_user['username']}")
                  notifications_collection.update_one({'chat_id': other_data['chat_id']}, {'$set': {'message' : other_data['message'] + '\n' + f"{user['first_name']} {user['last_name']} {user['username']}"}})
              else:
                notifications_collection.update_one({'chat_id': other_data['chat_id']}, {'$set': {'not_message' : other_data['not_message'] + '\n' + f"{user['first_name']} {user['last_name']} {user['username']}"}})
                not_nearby_users.append(f"{other_user['first_name']} {other_user['last_name']} {other_user['username']}")
          message = 'users near you: \n' + '\n'.join(nearby_users)
          not_message = 'users near you: \n' + '\n'.join(not_nearby_users)
          prev_message_id = data['message_id']
          if prev_message_id:
              if message != data['message']:
                bot.edit_message_text(chat_id=chat_id, message_id=prev_message_id, text=message)
              notifications_collection.update_one({'chat_id': chat_id}, {'$set': {'message_id': prev_message_id, 'message' : message, 'not_message' : not_message}})             
          else:
              sent_message = bot.send_message(chat_id, message)
              notifications_collection.update_one({'chat_id': chat_id}, {'$set':{'chat_id': chat_id, 'message_id': sent_message.message_id, 'message' : message, 'not_message' : not_message}})
      else: 
         return
      i += REFRESH_RATE
      sleep(REFRESH_RATE)

@bot.message_handler(commands=['start'])
def handle_start(message):
    chat_id = message.chat.id
    user = collection.find_one({'id': chat_id})
    if user:
        markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
        button_end = telebot.types.KeyboardButton(text="/end")
        markup.add(button_end)
        user = collection.find_one({'id': chat_id})
        if not user:
          return
        bot.send_message(chat_id, "You are already using the bot. \nYou can use /end to exit", reply_markup = markup )
    else:
        user_data = {
            'id': chat_id,
            'status': AWAIT_LOCATION
        }
        collection.insert_one(user_data)
        notification_data = {
            'chat_id': chat_id,
            'message': '',
            'not_message' : '',
            'message_id': 0
        }
        notifications_collection.insert_one(notification_data)
        Thread(target = find_nearby_users_periodic, args=[chat_id, collection]).start()
        markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
        button_location = telebot.types.KeyboardButton(text="Share Location", request_location=True)
        button_end = telebot.types.KeyboardButton(text="/end")
        markup.add(button_location, button_end)
        bot.send_message(chat_id, "🌟 Welcome to FindMeAFriend Bot! 🤖 Ready to connect? To find friends nearby, please tap \"Share Location\" below. 📍 If you change your mind, simply hit /end. Let the fun begin! 💬✨", reply_markup=markup)
        bot.register_next_step_handler(message, handle_location_button)

def handle_location_button(message):
    chat_id = message.chat.id
    user = collection.find_one({'id': chat_id})
    if message.text == '/end':
        if user:
            markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
            button_start = telebot.types.KeyboardButton(text="/start")
            markup.add(button_start)
            user = collection.find_one({'id': chat_id})
            if not user:
              return
            bot.send_message(chat_id, END_MESSAGE,reply_markup = markup)
            user = collection.find_one({'id': chat_id})
            if not user:
              return
            collection.delete_one({'id': chat_id})
            delete_notifications(chat_id, notifications_collection)
        else:
            markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
            button_start = telebot.types.KeyboardButton(text="/start")
            markup.add(button_start)
            user = collection.find_one({'id': chat_id})
            if not user:
              return
            bot.send_message(chat_id, "You are currently inactive. Please use /start to start.",reply_markup = markup)
    else:
        if message.location:
            user = message.from_user
            user_data = {
                'id': user.id,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'latitude': message.location.latitude,
                'longitude': message.location.longitude,
                'username': user.username,
                'status': AWAIT_ACTIVITY,
                'activity': '',
            }
            if user_data['last_name'] == None:
                user_data['last_name'] = ''
            if user_data['first_name'] == None:
                user_data['first_name'] = ''
            if user_data['username']:
               user_data['username'] = '@' + user_data['username']
            else:
               user_data['usersname'] = ''
            collection.update_one({'id': chat_id}, {'$set': user_data})
            markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
            button_end = telebot.types.KeyboardButton(text="/end")
            markup.add(button_end)
            user = collection.find_one({'id': chat_id})
            if not user:
              return
            bot.send_message(chat_id,"Awesome! 🌟 Thanks for sharing your location. Now, what activity are you interested in doing with a new friend? 🤝 Type your activity, and let's make some exciting plans! 🚀 If you change your mind, use /end to exit. 💬✨",reply_markup=markup)
            user = collection.find_one({'id': chat_id})
            if not user:
              return
            bot.register_next_step_handler(message, handle_activity_or_exit)
        else:
            markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
            button_location = telebot.types.KeyboardButton(text="Share Location", request_location=True)
            button_end = telebot.types.KeyboardButton(text="/end")
            markup.add(button_location, button_end)
            user = collection.find_one({'id': chat_id})
            if not user:
              return
            bot.send_message(chat_id, "Oops! 🌍 It seems like there was an issue with the location you provided. Please use the 'Share Location' button or type /end to exit. Let's get you back on track! 📍🔄", reply_markup = markup)
            user = collection.find_one({'id': chat_id})
            if not user:
              return
            bot.register_next_step_handler(message, handle_location_button)

def handle_activity_or_exit(message):
    chat_id = message.chat.id
    user = collection.find_one({'id': chat_id})
    if not message.text:
      markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
      button_end = telebot.types.KeyboardButton(text="/end")
      markup.add(button_end)
      user = collection.find_one({'id': chat_id})
      if not user:
        return
      bot.send_message(chat_id, "Uh-oxh! 🤷‍♂️ It looks like the activity you shared is invalid. Please provide a different activity or type /end to exit. Let's find a more suitable plan for you! 🔄💬",reply_markup=markup)
      user = collection.find_one({'id': chat_id})
      if not user:
        return
      bot.register_next_step_handler(message, handle_activity_or_exit)
    elif message.text == '/end':
        if user:
            markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
            button_start = telebot.types.KeyboardButton(text="/start")
            markup.add(button_start)
            user = collection.find_one({'id': chat_id})
            if not user:
              return
            bot.send_message(chat_id, END_MESSAGE,reply_markup = markup)
            user = collection.find_one({'id': chat_id})
            if not user:
              return
            collection.delete_one({'id': chat_id})
            delete_notifications(chat_id, notifications_collection)
        else:
            bot.send_message(chat_id, "You are not currently in the process.")
    elif message.text == '/changelocation' or message.text == '/changeactivity' or message.text == '/start' :
      user = collection.find_one({'id': chat_id})
      if not user:
        return
      markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
      button_end = telebot.types.KeyboardButton(text="/end")
      markup.add(button_end)
      user = collection.find_one({'id': chat_id})
      if not user:
        return
      bot.send_message(chat_id, "Uh-oh! 🤷‍♂️ It looks like the activity you shared is invalid. Please provide a different activity or type /end to exit. Let's find a more suitable plan for you! 🔄💬",reply_markup=markup)
      user = collection.find_one({'id': chat_id})
      if not user:
        return
      bot.register_next_step_handler(message, handle_activity_or_exit)
    else:
        activity = correct_activity(message.text.replace(' ',''))
        if activity == None:
            markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
            button_end = telebot.types.KeyboardButton(text="/end")
            markup.add(button_end)
            user = collection.find_one({'id': chat_id})
            if not user:
              return
            bot.send_message(chat_id, "Uh-oh! 🤷‍♂️ It looks like the activity you shared is invalid. Please provide a different activity or type /end to exit. Let's find a more suitable plan for you! 🔄💬",reply_markup=markup)
            bot.register_next_step_handler(message, handle_activity_or_exit)
            return
        user_data = {
            'activity': activity,
            'status': AWAIT_END,
        }
        user = collection.find_one({'id': chat_id})
        if not user:
          return
        collection.update_one({'id': chat_id}, {'$set': user_data})
        if not user:
          return
        bot.send_message(chat_id, "Thanks for sharing your activity! 🌟 We've started finding people nearby who share your interests. Sit tight, and we'll notify as we find a potential friends. 🤝 If you need to leave, simply use /end.💬✨")

@bot.message_handler(commands=['end'])
def handle_end(message):
    chat_id = message.chat.id
    user = collection.find_one({'id': chat_id})
    if user and (user['status'] == AWAIT_LOCATION or user['status'] == AWAIT_ACTIVITY or user['status'] == AWAIT_END):
        markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
        button_start = telebot.types.KeyboardButton(text="/start")
        markup.add(button_start)
        user = collection.find_one({'id': chat_id})
        if not user:
          return
        bot.send_message(chat_id, END_MESSAGE,reply_markup = markup)
        collection.delete_one({'id': chat_id})
        delete_notifications(chat_id, notifications_collection)
    else:
        markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
        button_start = telebot.types.KeyboardButton(text="/start")
        markup.add(button_start)
        bot.send_message(chat_id, "Seems like you've been away for a bit! 🌟 Ready to mingle? Start a new adventure by typing /start whenever you're ready to connect with friends nearby! 💬🚀",reply_markup = markup)

def delete_notifications(chat_id, notifications_collection, temp = False):
    if notifications_collection.find_one({'chat_id': chat_id}):
        message_id = notifications_collection.find_one({'chat_id': chat_id})['message_id']
        if message_id:
           bot.delete_message(chat_id=chat_id, message_id=message_id)
        notification_data = {
            'chat_id': chat_id,
            'message': '',
            'not_message' : '',
            'message_id': None
        }
        if temp:
          notifications_collection.update_one({'chat_id': chat_id}, {'$set':notification_data})
        else:
          notifications_collection.delete_one({'chat_id': chat_id})

def restart():
    data = collection.find()
    for user in data:
        if user['status'] == AWAIT_END:
            Thread(target = find_nearby_users_periodic, args=[user['id'], collection]).start()    
        else:
            markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
            button_start = telebot.types.KeyboardButton(text="/start")
            markup.add(button_start)
            bot.send_message(user['id'], "Oopsie! 😮 An unexpected error occurred on our end. We're working to fix it! Please use /start to restart your journey. Let's get you back on track! 🚀💬", reply_markup = markup)
            collection.delete_one({'id': user['id']})
            delete_notifications(user['id'], notifications_collection)

@bot.message_handler(commands=['changelocation'])
def handle_changelocation_request(message):
    chat_id = message.chat.id
    user = collection.find_one({'id': chat_id})
    if user and user['status'] == AWAIT_END:
        collection.update_one({'id': chat_id}, {'$set': {'status': AWAIT_LOCATION}})
        delete_notifications(chat_id, notifications_collection, True)
        markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
        button_location = telebot.types.KeyboardButton(text="Share Location", request_location=True)
        button_end = telebot.types.KeyboardButton(text="/end")
        markup.add(button_location, button_end)
        user = collection.find_one({'id': chat_id})
        if not user:
          return
        bot.send_message(chat_id, "Oh, sweet! 🌍 Ready to explore new horizons? Please share your new location or use /end to cancel. Let's make sure you're right where you want to be! 📍💬", reply_markup=markup)
        bot.register_next_step_handler(message, handle_location_button_change_request)
    else:
        markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
        button_start = telebot.types.KeyboardButton(text="/start")
        markup.add(button_start)
        bot.send_message(chat_id, "Oopsie! 🌼 You cannot change your location at this stage. Please use /start to begin a new adventure. Let's keep the excitement going! 🚀💬", reply_markup=markup)

def handle_location_button_change_request(message):
    chat_id = message.chat.id
    user = collection.find_one({'id': chat_id})
    if message.text == '/end':
        if user:
            user = message.from_user
            user_data = {
                'status': AWAIT_END,
            }
            collection.update_one({'id': chat_id}, {'$set': user_data})
            markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
            button_end = telebot.types.KeyboardButton(text="/end")
            markup.add(button_end)
            user = collection.find_one({'id': chat_id})
            if not user:
              return
            bot.send_message(chat_id, "Location change canceled! Phew! 😅 Let me know if you need anything else or just type /start to begin a new adventure. 🚀💬", reply_markup=markup)
    else:
        if message.location:
            user = message.from_user
            user_data = {
                'latitude': message.location.latitude,
                'longitude': message.location.longitude,
                'status': AWAIT_END,
            }
            collection.update_one({'id': chat_id}, {'$set': user_data})
            markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
            button_end = telebot.types.KeyboardButton(text="/end")
            markup.add(button_end)
            user = collection.find_one({'id': chat_id})
            if not user:
              return
            bot.send_message(chat_id, "Location updated successfully! 🌟 Yay! You're exactly where you want to be. Let's continue the fun! 🗺️💬", reply_markup=markup)
        else:
            markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
            button_location = telebot.types.KeyboardButton(text="Share Location", request_location=True)
            button_end = telebot.types.KeyboardButton(text="/end")
            markup.add(button_location, button_end)
            user = collection.find_one({'id': chat_id})
            if not user:
              return
            bot.send_message(chat_id, "Oops! 🙊 Invalid input. Please share your location or use /end to cancel. Let's make sure you're in the perfect spot! 📍💬", reply_markup=markup)
            bot.register_next_step_handler(message, handle_location_button_change_request)

@bot.message_handler(commands=['changeactivity'])
def handle_changeactivity_request(message):
    chat_id = message.chat.id
    user = collection.find_one({'id': chat_id})
    if user and user['status'] == AWAIT_END:
        collection.update_one({'id': chat_id}, {'$set': {'status': AWAIT_ACTIVITY}}) 
        delete_notifications(chat_id, notifications_collection, True)
        user = collection.find_one({'id': chat_id})
        if not user:
            return
        bot.send_message(chat_id, "Aww, sure thing! 🔄 Please share your new exciting activity or type /end to cancel the change. Let's keep the fun going! 💬🌈")
        bot.register_next_step_handler(message, handle_activity_change_request)
    else:
        markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
        button_start = telebot.types.KeyboardButton(text="/start")
        markup.add(button_start)
        bot.send_message(chat_id, "Oopsie daisy! 🌼 You cannot change your activity at this stage, but don't worry, you're doing great! Just type /start to begin a new adventure. 🚀💬", reply_markup=markup)

def handle_activity_change_request(message):
    chat_id = message.chat.id
    user = collection.find_one({'id': chat_id})
    if not message.text or message.text == '/changelocation' or message.text == '/changeactivity' or message.text == '/start':
        markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
        button_end = telebot.types.KeyboardButton(text="/end")
        markup.add(button_end)
        user = collection.find_one({'id': chat_id})
        if not user:
            return
        bot.send_message(chat_id, "Oh no! 🙈 It seems like the activity you shared is a bit tricky. Please provide a different activity or type /end to cancel. Let's find something super fun! 🎉💬", reply_markup=markup)
        bot.register_next_step_handler(message, handle_activity_change_request)
    elif message.text == '/end':
        if user:
            user = message.from_user
            user_data = {
                'status': AWAIT_END,
            }
            collection.update_one({'id': chat_id}, {'$set': user_data})
            markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
            button_end = telebot.types.KeyboardButton(text="/end")
            markup.add(button_end)
            bot.send_message(chat_id, "Activity change canceled! Phew! 😅 Let me know if you need anything else or just type /start to begin a new adventure. 🚀💬", reply_markup=markup)
    else:
        activity = correct_activity(message.text.replace(' ',''))
        if activity is None:
            markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
            button_end = telebot.types.KeyboardButton(text="/end")
            markup.add(button_end)
            user = collection.find_one({'id': chat_id})
            if not user:
                return
            bot.send_message(chat_id, "Oh snap! 🙊 It looks like the activity you shared is a bit tricky. Please provide a different activity or type /end to cancel. Let's find something super fun! 🎉💬", reply_markup=markup)
            bot.register_next_step_handler(message, handle_activity_change_request)
            return
        user_data = {
            'activity': activity,
            'status': AWAIT_END,
        }
        collection.update_one({'id': chat_id}, {'$set': user_data})
        user = collection.find_one({'id': chat_id})
        if not user:
            return
        bot.send_message(chat_id, "Activity updated successfully! 🌟 Yay! 🤝💬")

if __name__ == '__main__':
    restart()
    bot.infinity_polling(skip_pending=True)
