from typing import List, Tuple
from updates.updates_db import UpdatesDB
from datetime import datetime
import openai

class UpdatesManager:
    """
    Manages status updates for team members.
    """

    def __init__(self, updates_db: UpdatesDB):
        """
        Initializes a new UpdatesManager instance.

        Args:
            updates_db: The UpdatesDB object that handles database operations.
        """
        self.updates_db = updates_db

    def insert_status(self, discord_id: int, status: str, time_zone: str):
        """
        Inserts a new status update.

        Args:
            discord_id: The Discord ID of the team member.
            status: The status update.
        """
        self.updates_db.insert_status(discord_id, status, time_zone)

    def update_summarized_status(self, discord_id: int, summarized_status: str):
        """
        Updates the summarized status for the most recent update for a given user.

        Args:
            discord_id: The Discord ID of the team member.
            summarized_status: The summarized status update.
        """
        self.updates_db.update_summarized_status(discord_id, summarized_status)

    def get_weekly_checkins_count(self, discord_id: int, time_zone: str) -> int:
        """
        Fetches the number of check-ins for a given user in the current week.

        Args:
            discord_id: The Discord ID of the user.
            time_zone: The time zone of the user.

        Returns:
            The count of check-ins in the current week.
        """
        return self.updates_db.get_weekly_checkins_count(discord_id, time_zone)
    
    def get_all_statuses_for_user(self, discord_id: int) -> List[dict]:
        """
        Fetches all status updates (both raw and summarized) for a given user.

        Args:
            discord_id: The Discord ID of the user.

        Returns:
            A list of dictionaries, each containing the status update details for a given record.
        """
        return self.updates_db.get_all_statuses_for_user(discord_id)


    async def generate_daily_summary(self, user_message: str) -> str:
        """
        Generates a daily summary of the user's message using a large language model.

        Args:
            user_message: The user's message that needs to be summarized.

        Returns:
            The summarized message.
        """
        # Prepare a system message to guide OpenAI's model
        system_message = "Please summarize the user's update into two sections: 'Did' for tasks completed yesterday and 'Do' for tasks planned for today."
        
        # Prepare the messages input for ChatCompletion
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message}
        ]
        
        # Specify the model engine you want to use
        model_engine = "gpt-3.5-turbo-0613"
        
        try:
            # Make an API call to OpenAI's ChatCompletion
            response = openai.ChatCompletion.create(
                model=model_engine,
                messages=messages
            )
            
            # Extract the generated text
            summarized_message = response['choices'][0]['message']['content'].strip()

            return summarized_message
            
        except Exception as e:
            print(f"An error occurred while generating the summary: {e}")
            return "Error in generating summary"

    async def generate_weekly_summary(self, discord_id: int, start_date: datetime, end_date: datetime) -> str:
        """
        Generates a weekly summary of the user's status updates using a large language model.

        Args:
            discord_id: The Discord ID of the user.
            start_date: The start date of the date range.
            end_date: The end date of the date range.

        Returns:
            The summarized weekly status update.
        """
        # Fetch all raw status updates for the specified date range using the new method in UpdatesDB
        weekly_statuses = self.updates_db.get_statuses_in_date_range(discord_id, start_date, end_date)

        if not weekly_statuses:
            return "There are no status updates for this week."
        
        # Combine all raw statuses into a single string
        combined_statuses = "\n".join(weekly_statuses)
        
        # Prepare a system message to guide OpenAI's model for weekly summary
        system_message = "Please generate a comprehensive weekly summary based on the provided daily status updates, including only tasks that have been accomplished. Ignore tasks that are not in the 'Did' section."
        
        # Prepare the messages input for ChatCompletion
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": combined_statuses}
        ]
        
        # Specify the model engine you want to use
        model_engine = "gpt-4-0613"
        
        try:
            # Make an API call to OpenAI's ChatCompletion
            response = openai.ChatCompletion.create(
                model=model_engine,
                messages=messages
            )
            
            # Extract the generated text
            weekly_summary = response['choices'][0]['message']['content'].strip()

            return weekly_summary
            
        except Exception as e:
            print(f"An error occurred while generating the weekly summary: {e}")
            return "Error in generating weekly summary"
        
    async def summarize_technical_updates(self, commit_messages: List[str]) -> str:
        """
        Summarizes the technical updates based on commit messages.

        Args:
            commit_messages: List of commit messages for the day.

        Returns:
            A summarized version of the technical updates.
        """

        # Combine commit messages into a single string for the LLM
        combined_commits = "\n".join(commit_messages)

        # If there are no commit messages, return a default message
        if not combined_commits:
            return "No technical updates found based on commit messages."

        # Summarization using LLM
        system_message = "Please provide a concise summary of the technical updates based on the provided commit messages."

        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": combined_commits}
        ]

        model_engine = "gpt-3.5-turbo-0613"

        try:
            response = openai.ChatCompletion.create(
                model=model_engine,
                messages=messages
            )

            # Extract the generated summary
            summarized_message = response['choices'][0]['message']['content'].strip()

            return summarized_message

        except Exception as e:
            print(f"An error occurred while generating the technical summary: {e}")
            return "Error in generating technical summary."

    async def summarize_feedback_and_revisions(self, original_report: str, feedback: str) -> str:
        """
        Takes the original report and user feedback and generates a revised summary.

        Args:
            original_report: The original summarized report.
            feedback: The user's feedback or suggested edits.

        Returns:
            The revised summary.
        """
        # Prepare a system message to guide OpenAI's model
        system_message = "Revise the original report based on the user's feedback."

        # Prepare the messages input for ChatCompletion
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": f"Original Report: {original_report}"},
            {"role": "user", "content": f"Feedback: {feedback}"}
        ]
        
        # Specify the model engine you want to use
        model_engine = "gpt-3.5-turbo-0613"
        
        try:
            # Make an API call to OpenAI's ChatCompletion
            response = openai.ChatCompletion.create(
                model=model_engine,
                messages=messages
            )
            
            # Extract the generated text
            revised_summary = response['choices'][0]['message']['content'].strip()

            return revised_summary
            
        except Exception as e:
            print(f"An error occurred while generating the revised summary: {e}")
            return "Error in generating revised summary"

    async def summarize_non_technical_updates(self, update: str) -> str:
        """
        Summarizes a non-technical update using a large language model.

        Args:
            update: The raw non-technical update provided by the user.

        Returns:
            The summarized non-technical update.
        """

        # System message to guide the LLM for a concise summary
        system_message = "Please provide a concise summary of the non-technical update shared by the user."

        # Prepare the messages input for ChatCompletion
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": update}
        ]

        # Specify the model engine you want to use
        model_engine = "gpt-3.5-turbo-0613"

        try:
            # Make an API call to OpenAI's ChatCompletion
            response = openai.ChatCompletion.create(
                model=model_engine,
                messages=messages
            )

            # Extract the generated summary
            summarized_message = response['choices'][0]['message']['content'].strip()

            return summarized_message

        except Exception as e:
            print(f"An error occurred while generating the non-technical summary: {e}")
            return "Error in generating summary"

    async def summarize_goals_for_the_day(self, goals: str) -> str:
        """
        Summarizes the user's goals for the day using a large language model.

        Args:
            goals: The user's raw input on their goals for the day.

        Returns:
            The summarized goals for the day.
        """
        # Initiate the conversation with the model
        system_message = "Please provide a concise summary of the user's goals for today."
        
        # Prepare the messages input for ChatCompletion
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": goals}
        ]
        
        # Specify the model engine you want to use (this is an example and can be adjusted based on your needs)
        model_engine = "gpt-3.5-turbo-0613"
        
        try:
            # Provide user's input and retrieve model's response
            response = openai.ChatCompletion.create(
                model=model_engine,
                messages=messages
            )
            
            # Extract the generated text
            summarized_goals = response['choices'][0]['message']['content'].strip()

            # Return the summary
            return summarized_goals
                
        except Exception as e:
            print(f"An error occurred while generating the goals summary: {e}")
            return "Error in generating goals summary"