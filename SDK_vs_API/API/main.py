from netfree_unstrict_ssl import unstrict_ssl
unstrict_ssl()
from API.agent import run_agent

def main():
    user_text = input("Describe your event: ")

    answer = run_agent(user_text)

    print("\nAgent recommendation:")
    print(answer)


if __name__ == "__main__":
    main()