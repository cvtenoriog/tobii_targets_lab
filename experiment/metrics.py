import csv

path = "logs/P01_20261006_130514.log"

def count_events_successful(path):
    with open(path, "r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        successful_count = sum(1 for row in reader if row["hit"] == "1")
    return successful_count

def count_events_unsuccessful(path):
    with open(path, "r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        unsuccessful_count = sum(1 for row in reader if row["hit"] == "0")
    return unsuccessful_count

def report_metrics(path):
    successful_count = count_events_successful(path)
    unsuccessful_count = count_events_unsuccessful(path)
    total_count = successful_count + unsuccessful_count
    success_rate = (successful_count / total_count) * 100 if total_count > 0 else 0

    print(f"Total Events: {total_count}")
    print(f"Successful Events: {successful_count}")
    print(f"Unsuccessful Events: {unsuccessful_count}")
    print(f"Success Rate: {success_rate:.2f}%")

def main():
    report_metrics(path)

if __name__ == "__main__":
    main()