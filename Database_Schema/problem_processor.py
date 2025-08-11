import cloudscraper
from bs4 import BeautifulSoup
import logging
import re
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()
batch_size = 100

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

input_file = '../codeforces.txt'


def clean_text(text):
    text = text.encode('ascii', 'ignore').decode('ascii')
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def extract_problem_details(url):
    try:
        scraper = cloudscraper.create_scraper()
        response = scraper.get(url)

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')

            problem_name = soup.find('div', class_='title').text.strip()
            problem_statement = soup.find('div', class_='problem-statement').text.strip()
            problem_statement = clean_text(problem_statement)  # Clean the problem statement

            tags = soup.find_all('span', class_='tag-box')
            topics = [tag.text.strip() for tag in tags]

            return {
                'problem_name': problem_name,
                'problem_link': url,
                'platform': 'Codeforces',
                'topics': topics,
                'problem_statement': problem_statement
            }
        else:
            logging.error(f"Failed to fetch URL {url}: HTTP {response.status_code}")
            return None
    except Exception as e:
        logging.error(f"Error processing URL {url}: {e}")
        return None


def insert_problems_in_batches(data, batch_size=10):
    try:
        conn = psycopg2.connect(
            user=os.getenv("user"),
            password=os.getenv("password"),
            host=os.getenv("host"),
            port=os.getenv("port"),
            dbname=os.getenv("dbname")
        )
        cur = conn.cursor()

        insert_query = '''
        INSERT INTO problems (problem_name, problem_link, platform, problem_statement, topics)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (problem_link) DO NOTHING;
        '''

        for i in range(0, len(data), batch_size):
            batch = data[i:i + batch_size]
            values = [
                (
                    problem['problem_name'],
                    problem['problem_link'],
                    problem['platform'],
                    problem['problem_statement'],
                    problem['topics']
                )
                for problem in batch
            ]
            cur.executemany(insert_query, values)
            conn.commit()
            logging.info(f"Inserted batch {i // batch_size + 1}")
    except Exception as e:
        logging.error(f"Error inserting batch: {e}")
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    problems = []

    with open(input_file, 'r') as file:
        for line in file:
            url = line.strip()
            if url:
                logging.info(f"Processing: {url}")
                details = extract_problem_details(url)
                if details:
                    problems.append(details)

                if len(problems) == batch_size:
                    insert_problems_in_batches(problems, batch_size= batch_size)
                    problems = []

    if problems:
        insert_problems_in_batches(problems, batch_size=100)