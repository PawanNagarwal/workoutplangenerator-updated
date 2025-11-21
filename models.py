import os
import re
import json
import openai
import streamlit as st
from typing import Dict, List
from dotenv import load_dotenv
from utils import update_session_usage, calculate_token_costs,calculate_calories_burned,estimate_exercise_duration
from config import FITNESS_LEVEL_DESCRIPTIONS

# Load environment variables
load_dotenv()

class WorkoutPlanGenerator:
    def __init__(self):
        self.client = None
        self.api_key = os.getenv('OPENAI_API_KEY')
        if self.api_key:
            openai.api_key = self.api_key
            self.client = openai
    
    def set_api_key(self, api_key: str):
        """Set OpenAI API key"""
        openai.api_key = api_key
        self.client = openai
    
    def get_fitness_level_description(self, level: str) -> str:
        """Get fitness level description"""
        return FITNESS_LEVEL_DESCRIPTIONS.get(level, "Unknown level")
    
    def create_prompt(self, user_data: Dict) -> str:
        """Create comprehensive prompt for GPT-4o focused on detailed workout plans in JSON format"""
        
        # Determine exercise types based on workout preferences
        exercise_types_text = ""
        if user_data['workout_preferences']:
            if isinstance(user_data['workout_preferences'], list):
                exercise_types_text = f"- Preferred Exercise Types: {', '.join(user_data['workout_preferences'])}"
            else:
                exercise_types_text = f"- Preferred Exercise Types: {user_data['workout_preferences']}"
        
        # Equipment preference text
        equipment_text = ""
        if user_data.get('available_equipment'):
            equipment_text = f"- Available Equipment: {', '.join(user_data['available_equipment'])}"
        
        # Health limitations text
        limitations_text = ""
        if user_data.get('health_limitations'):
            limitations_text = f"- Health Limitations: {user_data['health_limitations']}"
        
        # Target areas text
        target_areas_text = ""
        if user_data.get('target_areas'):
            target_areas_text = f"- Target Areas: {', '.join(user_data['target_areas'])}"
        
        prompt = f"""Create a comprehensive, personalized {user_data['weekly_frequency']}-day workout plan based on the following information:

PERSONAL INFORMATION:
- Name: {user_data.get('name', 'User')}
- Age: {user_data['age']} years
- Gender: {user_data['gender']}
- Weight: {user_data.get('weight', 'N/A')}
- Height: {user_data.get('height', 'N/A')}

FITNESS PROFILE:
- Current Fitness Level: {user_data['fitness_level']}
- Primary Fitness Goal: {user_data['goal']}
- Training Days per Week: {user_data.get('training_days_per_week', user_data['weekly_frequency'])}
- Session Duration: {user_data.get('session_duration', user_data['duration_per_session'])} minutes
{exercise_types_text}

EQUIPMENT & PREFERENCES:
{equipment_text}    
{target_areas_text}   

HEALTH & LIMITATIONS:
{limitations_text}
- Exercises to Avoid: {user_data.get('exercises_to_avoid', 'None')}

ADDITIONAL INFORMATION:
- Additional Notes: {user_data.get('additional_notes', 'None')}

WORKOUT PLAN REQUIREMENTS:
Create a detailed workout plan in JSON format that includes:
- Day-wise breakdown for {user_data['weekly_frequency']} workout days
- Each day should have a specific workout type (Strength, Cardio, Flexibility, HIIT/Circuit, etc.)
- Exercise-level details for each workout
- Progressive difficulty based on fitness level  
- Proper warm-up and cool-down exercises  
- Equipment requirements and alternatives  

Return the response in the following JSON structure:
{{
  "workout_plan": {{
    "day_1": {{
      "day_name": "Day 1 - Monday",
      "workout_type": "Strength Training",
      "workout_duration": {user_data.get('session_duration', user_data['duration_per_session'])},
      "exercises": [
        {{
          "exercise_name": "Exercise name",
          "exercise_type": "Compound/Isolation/Warm-up/Cooldown",
          "equipment_required": "Equipment needed or Bodyweight",
          "target_muscle_group": "Primary muscle groups targeted",
          "total_sets": 1,
          "reps": "Number of repetitions or duration",
          "tempo": "3-1-2 (3 sec down, 1 sec pause, 2 sec up)",
          "rest_time": "Rest duration between sets (e.g., 60s)",
          "weight": "Recommended weight based on fitness level",
          "speed_level": "For cardio exercises: Slow/Moderate/Fast",
          "breathing_pattern": "Inhale/exhale rhythm instructions",
          "superset_indicator": "None or paired exercise name"
        }}
      ]
    }},
    // Continue for all {user_data['weekly_frequency']} workout days
  }}
}}

Guidelines:
1. Provide specific rep ranges appropriate for the fitness level:
   - Beginner: 8-12 reps, lighter weights, more rest
   - Intermediate: 10-15 reps, moderate intensity
   - Advanced: 12-20 reps or advanced techniques
2. Include proper progression and variety across days
3. Balance different muscle groups throughout the week
4. Include warm-up and cool-down exercises for each session
5. Provide equipment alternatives when possible
6. Match workout types to user's preferred exercise types
7. Ensure total workout duration matches specified session time
8. Include proper rest periods between sets
9. Add tempo instructions for strength exercises
10. Include breathing patterns for all exercises
11. Consider health limitations and exercises to avoid
12. Focus on target areas if specified

Workout Type Distribution for {user_data['weekly_frequency']} days:
- Focus on {user_data['goal']} with {user_data['workout_preferences']} preferences
- Ensure balanced approach with strength, cardio, and recovery
- Progressive overload principles for continuous improvement"""
        
        return prompt
    
    def generate_workout_plan(self, user_data: Dict) -> str:
        """Generate workout plan using OpenAI GPT-4o with JSON output"""
        try:
            prompt = self.create_prompt(user_data)
            print(prompt)
            
            response = openai.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a certified personal trainer and exercise physiologist with over 15 years of experience in creating personalized workout plans. You specialize in strength training, cardiovascular fitness, functional movement, and injury prevention. Always provide specific exercise parameters including sets, reps, tempo, and rest periods. Always respond in valid JSON format."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                response_format={"type": "json_object"},
            )
            print(response)
            # Extract token usage information
            usage = response.usage
            input_tokens = usage.prompt_tokens
            output_tokens = usage.completion_tokens
            
            # Update session usage tracking
            update_session_usage(input_tokens, output_tokens, "Workout Plan Generation")
            
            # Store latest usage in session state for display
            st.session_state.latest_usage = {
                'input_tokens': input_tokens,
                'output_tokens': output_tokens,
                'total_tokens': input_tokens + output_tokens,
                'costs': calculate_token_costs(input_tokens, output_tokens)   
            }
            
            return response.choices[0].message.content
        
        except Exception as e:
            raise Exception(f"Error generating workout plan: {str(e)}")
    
    def parse_workout_plan(self, workout_plan_json: str) -> List[Dict]:
        """Parse the JSON workout plan into structured daily workout data"""
        try:
            # Parse JSON response
            workout_data = json.loads(workout_plan_json)
            
            # Extract workout plan data
            if "workout_plan" in workout_data:
                plan_data = workout_data["workout_plan"]
            else:
                plan_data = workout_data
            
            days_data = []
            
            # Process each day
            for day_key in sorted(plan_data.keys()):
                day_info = plan_data[day_key]
                
                # Extract day number from key
                day_number = int(re.findall(r'\d+', day_key)[0]) if re.findall(r'\d+', day_key) else len(days_data) + 1
                
                day_data = {
                    'day': day_number,
                    'title': day_info.get('day_name', f'Day {day_number}'),
                    'workout_type': day_info.get('workout_type', 'Workout'),
                    'workout_duration': day_info.get('workout_duration', 0),
                    'exercises': []
                }
                
                # Process exercises for this day
                # Inside the exercise loop in parse_workout_plan method
                for exercise in day_info.get('exercises', []):
                    # Calculate estimated duration for this exercise
                    est_duration = estimate_exercise_duration(
                        exercise.get('total_sets', 1),
                        exercise.get('reps', '10'),
                        exercise.get('rest_time', '60s')
                    )
                    
                    # Calculate calories burned (if user weight is available)
                    calories_burned = 0.0
                    if 'form_data' in st.session_state and st.session_state.form_data.get('weight'):
                        weight_kg = st.session_state.form_data['weight']
                        calories_burned = calculate_calories_burned(
                            exercise.get('exercise_name', ''),
                            weight_kg,
                            est_duration,
                            exercise.get('exercise_type', '')
                        )
                    
                    exercise_data = {
                        'exercise_name': exercise.get('exercise_name', ''),
                        'exercise_type': exercise.get('exercise_type', ''),
                        'equipment_required': exercise.get('equipment_required', ''),
                        'target_muscle_group': exercise.get('target_muscle_group', ''),
                        'total_sets': exercise.get('total_sets', 1),
                        'reps': exercise.get('reps', ''),
                        'tempo': exercise.get('tempo', ''),
                        'rest_time': exercise.get('rest_time', ''),
                        'weight': exercise.get('weight', ''),
                        'speed_level': exercise.get('speed_level', ''),
                        'breathing_pattern': exercise.get('breathing_pattern', ''),
                        'superset_indicator': exercise.get('superset_indicator', 'None'),
                        'estimated_duration': est_duration,
                        'calories_burned': calories_burned
                    }

                    
                    # Only add exercise if it has required data
                    if exercise_data['exercise_name']:
                        day_data['exercises'].append(exercise_data)
                
                # Only add day if it has exercises
                if day_data['exercises']:
                    days_data.append(day_data)
            
            return days_data
            
        except json.JSONDecodeError as e:
            st.error(f"Error parsing JSON response: {str(e)}")
            return []
        except Exception as e:
            st.error(f"Error processing workout plan: {str(e)}")
            return []
