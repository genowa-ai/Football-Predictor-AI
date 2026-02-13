import psycopg2

# Connect
conn = psycopg2.connect(host="localhost", database="football_db", user="postgres", password="1004")
cursor = conn.cursor()

# 1. Count Total Matches
cursor.execute("SELECT COUNT(*) FROM matches")
total_matches = cursor.fetchone()[0]
print(f"Total Matches in DB: {total_matches}")

# 2. Check Wolves specifically
team_name = "Wolves" # or "Wolverhampton"
cursor.execute(f"SELECT COUNT(*) FROM matches m JOIN teams t ON m.home_team_id = t.team_id WHERE t.name = '{team_name}'")
wolves_home = cursor.fetchone()[0]
print(f"Matches where {team_name} was Home: {wolves_home}")

# 3. Check Man United
team_name = "Man United" 
cursor.execute(f"SELECT COUNT(*) FROM matches m JOIN teams t ON m.home_team_id = t.team_id WHERE t.name = '{team_name}'")
manu_home = cursor.fetchone()[0]
print(f"Matches where {team_name} was Home: {manu_home}")

conn.close()