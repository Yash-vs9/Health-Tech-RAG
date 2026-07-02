from nemoguardrails import LLMRails, RailsConfig

config = RailsConfig.from_path("config")

rails = LLMRails(config)


def get_guardrails_response(user_input):
    response = rails.generate(
        messages=[
            {
                "role": "user",
                "content": user_input
            }
        ]
    )

    return response