from dotenv import load_dotenv
from SDK.agent import run_agent

def main():
    load_dotenv()
    request = input("פרטי האירוע: ").strip()
    print(run_agent(request))

if __name__ == "__main__":
    main()
