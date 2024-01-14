# FindMeAFriend-Bot

This comprehensive Python script aims to create a social media-like experience on Telegram, helping users find friends with shared interests and activities. The bot employs the Telebot library for Telegram interaction, PyMongo for MongoDB integration, and Google's Generative AI for natural language processing.

## Dependencies

- **Telebot:** The Telegram bot library for Python.
- **PyMongo:** A MongoDB driver for Python.
- **Google Generative AI:** Google's language model API for natural language processing.

## Setup

1. Replace the following placeholders with your actual API tokens:
   - `genai.configure("REPLACE WITH GOOGLE API TOKEN")`
   - `telebot.TeleBot('TELEGRAM BOT TOKEN')`
   - `MongoClient('MONGO DB Token')`

2. Install required libraries using `pip install telebot pymongo`.

## Script Overview

### 1. Configuration and Initialization

   - Google Generative AI and Telebot are configured with their respective API tokens.
   - A connection to the MongoDB database is established.

### 2. Constants and Parameters

   - Various constants are defined, including the end message, user statuses, refresh rate, and timeout period.

### 3. Activity Processing Functions

   - `correct_activity`: Corrects spelling and grammar of the provided activity.
   - `check_activity`: Checks if two activities are related and can be done together easily.

### 4. Location-related Functions

   - `haversine_distance`: Calculates the haversine distance between two sets of latitude and longitude coordinates.
   - `auto_exit`: Deletes user data when the session times out.

### 5. User Notification Functions

   - `delete_notifications`: Deletes user notifications and messages.

### 6. Main Functionality

   - `find_nearby_users_periodic`: Periodically finds nearby users based on location and activity.

### 7. Telegram Bot Commands

   - `/start`: Initiates the bot and prompts users to share their location and activity.
   - `/end`: Ends the user's session.
   - `/changelocation`: Allows users to change their location.
   - `/changeactivity`: Allows users to change their activity.

### 8. Handlers for Telegram Bot Commands

   - `handle_start`: Handles the start command.
   - `handle_location_button`: Handles location sharing and activity input.
   - `handle_activity_or_exit`: Handles activity input or session end.
   - `handle_end`: Handles the end command.
   - `handle_changelocation_request`: Handles change location request.
   - `handle_location_button_change_request`: Handles location change request.
   - `handle_changeactivity_request`: Handles change activity request.
   - `handle_activity_change_request`: Handles activity change request.

### 9. Utility Functions

   - `restart`: Restarts the bot for users with an active session.
   - `delete_notifications`: Deletes notifications for a user.

### 10. Script Execution

   - Calls the `restart` function to handle active sessions.
   - Initiates the bot's infinite polling loop.

## Usage

1. **Run the Script:**
   - Execute the script to start the bot.

2. **User Interaction:**
   - Users interact with the bot using the defined commands.

3. **Social Connection:**
   - Acting like a social media app, the bot periodically finds nearby users based on their location and activity.

4. **Customization:**
   - Feel free to customize and enhance the script based on your specific requirements. Adjust functions, commands, and interactions to create a personalized and engaging social experience for users.

## Conclusion

This script aims to provide users with a unique and interactive social experience on Telegram, fostering connections and friendships based on shared interests and activities.```
