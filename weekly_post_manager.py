from datetime import datetime, timedelta
import json
import pytz
from typing import List
from status_db import StatusDB
from team_member import TeamMember

class WeeklyPostManager:
    """Manages the status post in a Discord channel."""
    
    def __init__(self, channel, team_members: List[TeamMember]):
        """
        Initializes a new WeeklyPostManager instance.

        Args:
            channel: The Discord channel where the weekly post will be sent.
            team_members: A list of TeamMember objects.
        """
        self.channel = channel
        self.team_members = team_members
        self.max_name_length = max((len(m.name) for m in team_members), default=0)
        self.editable_weekly_post = None
        self.load_weekly_post_data()

    def load_weekly_post_data(self):
        """
        Load the weekly post data from a JSON file.

        This function reads the 'weekly_post_data.json' file to get the ID and timestamp of the last
        weekly post. If the file does not exist, it sets the ID and timestamp to None.
        """
        try:
            # TODO: Use a database instead of a JSON
            with open("weekly_post_data.json", "r") as f:
                data = json.load(f)
            self.editable_weekly_post_id = data.get('post_id', None)
            self.weekly_post_timestamp = datetime.fromisoformat(data.get('timestamp')) if data.get('timestamp') else None
        except FileNotFoundError:
            self.editable_weekly_post_id = None
            self.weekly_post_timestamp = None
            # Create an empty weekly_post_data.json
            with open("weekly_post_data.json", "w") as f:
                json.dump({}, f)

    def save_weekly_post_data(self):
        """
        Save the weekly post data to a JSON file.

        This function writes the ID and timestamp of the current weekly post to the
        'weekly_post_data.json' file.
        """
        data = {
            'post_id': self.editable_weekly_post.id,
            'timestamp': datetime.now().isoformat()
        }
        with open("weekly_post_data.json", "w") as f:
            json.dump(data, f)

    async def initialize_post(self, db: StatusDB):
        """
        Initializes or retrieves the weekly status post on Discord.

        This function checks if a valid weekly post already exists for the current week.
        If it does, it retrieves that post. Otherwise, it sends a new message in the Discord
        channel with the list of team members and their statuses.
        """
        current_week_number = datetime.now().isocalendar()[1]
        saved_week_number = self.weekly_post_timestamp.isocalendar()[1] if self.weekly_post_timestamp else None

        # Skip initialization if the post already exists and is for the current week
        if self.editable_weekly_post_id and current_week_number == saved_week_number:
            self.editable_weekly_post = await self.channel.fetch_message(self.editable_weekly_post_id)
            return
        
        utc_now = pytz.utc.localize(datetime.utcnow())
        today_weekday = utc_now.weekday()
        last_monday = utc_now - timedelta(days=today_weekday)
        next_sunday = last_monday + timedelta(days=6)

        start_date = self.format_date(last_monday)
        end_date = self.format_date(next_sunday)

        # Add streaks to the member list
        member_list = []
        for m in self.team_members:
            streak = db.get_streak(m.discord_id)  # Fetch the streak from the database
            day_suffix = "day" if streak == 1 else "days"  # Choose the appropriate suffix
            member_list.append(f"# `{m.name.ljust(self.max_name_length)} {'❓' * 5} (Streak: {streak} {day_suffix})`")

        member_list_str = '\n'.join(member_list)

        await self.channel.send(f"# Weekly Status Updates")
        await self.channel.send(f"## {start_date} to {end_date}")
        if member_list_str:
            self.editable_weekly_post = await self.channel.send(f"{member_list_str}")
            self.save_weekly_post_data()  # Save the ID and timestamp after creating the post


    async def update_post(self, member: TeamMember, db: StatusDB):
        # Split the content into lines and find the line related to this member
        lines = self.editable_weekly_post.content.split('\n')
        line_to_edit = next((line for line in lines if member.name in line), None)

        if line_to_edit is None:
            return  # Name not found, do nothing
        
        # Remove the '#' and trim spaces
        line_to_edit = line_to_edit.replace("#", "").strip()

        # Extract the checkmarks/question marks and streak information
        name_end = line_to_edit.find(' ')
        marks_streak = line_to_edit[name_end:].strip()

        # Update the first question mark to a checkmark
        first_question_mark = marks_streak.find("❓")
        if first_question_mark == -1:
            return  # No question marks left, do nothing

        new_marks_streak = marks_streak[:first_question_mark] + "✅" + marks_streak[first_question_mark + 1:]

        # Update the streak count
        new_streak = db.get_streak(member.discord_id)
        new_streak_str = f"(Streak: {new_streak} {'day' if new_streak == 1 else 'days'})"

        # Reconstruct the new line for this member
        new_line = f"`{member.name.ljust(self.max_name_length)} {new_marks_streak.split('(')[0].strip()} {new_streak_str}`"

        # Replace the old line with the new line in the content
        new_content = self.editable_weekly_post.content.replace(line_to_edit, new_line)

        # Update the weekly post
        self.editable_weekly_post = await self.editable_weekly_post.edit(content=new_content)


    def has_all_checkmarks(self, member: TeamMember) -> bool:
        """
        Checks if a team member has all checkmarks (✅) in their status.

        Args:
            member: The TeamMember object to check.

        Returns:
            True if all checkmarks are present, False otherwise.
        """
        name_index = self.editable_weekly_post.content.find(member.name)
        if name_index == -1:
            return False  # Name not found, do nothing

        start_index = name_index + self.max_name_length + 1
        existing_line = self.editable_weekly_post.content[start_index:start_index + 5]
        
        return all([char == "✅" for char in existing_line])

    def format_date(self, dt: datetime) -> str:
        """
        Formats a datetime object into a human-readable string.

        Args:
            dt: The datetime object to format.

        Returns:
            A human-readable date string.
        """
        suffix = ['th', 'st', 'nd', 'rd']
        day = int(dt.strftime('%d'))
        if 4 <= day <= 20 or 24 <= day <= 30:
            suffix_index = 0  # use 'th'
        else:
            suffix_index = day % 10  # use 'st', 'nd', 'rd' as appropriate

        return dt.strftime(f"%B {day}{suffix[suffix_index]}")
    
    # TODO: Create a streak manager
    def update_streak(self, member: TeamMember, db: StatusDB) -> None:
        """
        Updates the streak count for a specific team member.

        This method fetches the current streak count for the member from the database,
        increments it by 1, and then updates the new streak back into the database.

        Args:
            member (TeamMember): The TeamMember object whose streak needs to be updated.
            db (StatusDB): The StatusDB object for interacting with the database.

        Returns:
            None
        """
        existing_streak = db.get_streak(member.discord_id)
        new_streak = existing_streak + 1
        db.update_streak(member.discord_id, new_streak)

    def reset_streaks(self, db: StatusDB) -> None:
        """
        Resets the streaks for all team members who have fewer than 5 checkmarks.

        This method iterates over all team members and checks if each member has
        at least 5 checkmarks for the current week. If not, their streak is reset
        to zero in the database.

        Args:
            db (StatusDB): The StatusDB object for interacting with the database.

        Returns:
            None
        """
        for member in self.team_members:
            if not self.has_minimum_checkmarks(member, 5):
                db.update_streak(member.discord_id, 0)

    def has_minimum_checkmarks(self, member: TeamMember, n: int) -> bool:
        """
        Checks if a team member has at least n checkmarks (✅) in their status.

        This method scans the status line for the given team member in the weekly
        Discord post and counts the number of checkmarks. It returns True if the
        count is at least n, otherwise False.

        Args:
            member (TeamMember): The TeamMember object to check.
            n (int): The minimum number of checkmarks required.

        Returns:
            bool: True if at least n checkmarks are present, False otherwise.
        """
        name_index = self.editable_weekly_post.content.find(member.name)
        if name_index == -1:
            return False  # Name not found, do nothing

        start_index = name_index + self.max_name_length + 1
        existing_line = self.editable_weekly_post.content[start_index:start_index + 5]

        return existing_line.count("✅") >= n

    async def rebuild_post(self, db: StatusDB):
        """
        Rebuilds the weekly status post with updated team members and alignment.

        This function regenerates the entire status post to make sure the alignment and check marks
        are correctly displayed for each team member. It also handles edge cases like adding the first
        member and removing the last one.

        Args:
            db (StatusDB): The StatusDB object for interacting with the database.

        Returns:
            None
        """
        # If there are team members but no editable post yet, create one for the first member
        if self.team_members and self.editable_weekly_post is None:
            first_member = self.team_members[0]
            streak = db.get_streak(first_member.discord_id)
            day_suffix = "day" if streak == 1 else "days"
            initial_content = f"# `{first_member.name.ljust(self.max_name_length)} {'❓' * 5} (Streak: {streak} {day_suffix})`"
            self.editable_weekly_post = await self.channel.send(initial_content)
            self.save_weekly_post_data()
            return

        # If no team members are left, delete the post and return
        if not self.team_members:
            if self.editable_weekly_post:
                await self.editable_weekly_post.delete()
            self.editable_weekly_post = None
            return
        
        member_list = []
        for m in self.team_members:
            # Extract the line related to this member
            lines = self.editable_weekly_post.content.split('\n')
            member_line = next((line for line in lines if m.name in line), None)
            
            # Default to five question marks
            existing_marks = "❓❓❓❓❓"

            if member_line:
                first_checkmark = member_line.find("✅")
                first_question_mark = member_line.find("❓")
                
                # Look for existing checkmarks
                if first_checkmark != -1:
                    existing_marks = member_line[first_checkmark:first_checkmark + 5]
                
                # If no checkmarks, look for existing question marks
                elif first_question_mark != -1:
                    existing_marks = member_line[first_question_mark:first_question_mark + 5]
            
            # Fetch the streak from the database
            streak = db.get_streak(m.discord_id)
            day_suffix = "day" if streak == 1 else "days"
            
            # Create the new line for the member
            new_line = f"# `{m.name.ljust(self.max_name_length)} {existing_marks} (Streak: {streak} {day_suffix})`"
            member_list.append(new_line)
        
        # Combine the lines into a single string
        new_content = '\n'.join(member_list)

        self.editable_weekly_post = await self.editable_weekly_post.edit(content=new_content)

    async def add_member_to_post(self, member: TeamMember, db: StatusDB):
        """
        Adds a new member to the editable weekly post and rebuilds it.

        Args:
            member (TeamMember): The new member to be added.
            db (StatusDB): The StatusDB object for interacting with the database.

        Returns:
            None
        """
        # Add the new member and update max_name_length
        self.team_members.append(member)
        self.max_name_length = max([len(m.name) for m in self.team_members])
        
        # Rebuild the post to reflect the changes
        await self.rebuild_post(db)

    async def remove_member_from_post(self, member: TeamMember, db: StatusDB):
        """
        Removes a member from the editable weekly post and rebuilds it.

        Args:
            member (TeamMember): The member to be removed.
            db (StatusDB): The StatusDB object for interacting with the database.

        Returns:
            None
        """
        # Remove the member and update max_name_length
        self.team_members = [m for m in self.team_members if m.discord_id != member.discord_id]
        self.max_name_length = max([len(m.name) for m in self.team_members]) if self.team_members else 0
        
        # Rebuild the post to reflect the changes
        await self.rebuild_post(db)

