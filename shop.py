from datetime import datetime

def format_today():
    # Get today's date
    today = datetime.today()
    
    # Format as dd/mm/yyyy
    date_str = today.strftime("%d/%m/%Y")
    
    # Get day of the week, month name, and year
    day_of_week = today.strftime("%A")   # e.g., Monday
    month_name = today.strftime("%B")    # e.g., March
    year = today.strftime("%Y")          # e.g., 2026
    
    return date_str, day_of_week, month_name, year

if __name__ == "__main__":
    date_str, day_of_week, month_name, year = format_today()
    print(f"Date (dd/mm/yyyy): {date_str}")
    print(f"Day of the week: {day_of_week}")
    print(f"Month: {month_name}")
    print(f"Year: {year}")