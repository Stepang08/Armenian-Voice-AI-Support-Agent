"""
scripts/generate_token.py — Generate a LiveKit access token for testing.

Usage:
  PYTHONPATH=. python3 scripts/generate_token.py --room bank-support --identity test-user
"""

import argparse
import os
from dotenv import load_dotenv
from livekit.api import AccessToken, VideoGrants

load_dotenv()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--room",     default="bank-support")
    parser.add_argument("--identity", default="test-user")
    args = parser.parse_args()

    api_key    = os.getenv("LIVEKIT_API_KEY",    "devkey")
    api_secret = os.getenv("LIVEKIT_API_SECRET", "secret")

    token = (
        AccessToken(api_key, api_secret)
        .with_identity(args.identity)
        .with_name(args.identity)
        .with_grants(VideoGrants(room_join=True, room=args.room))
        .to_jwt()
    )

    print(f"\nRoom:     {args.room}")
    print(f"Identity: {args.identity}")
    print(f"\nToken:\n{token}\n")


if __name__ == "__main__":
    main()
