from ulauncher.api.client.Extension import Extension
from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.shared.event import KeywordQueryEvent
from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem
from ulauncher.api.shared.action.RenderResultListAction import RenderResultListAction
from ulauncher.api.shared.action.HideWindowAction import HideWindowAction
from ulauncher.api.shared.action.CopyToClipboardAction import CopyToClipboardAction

import requests
import json


class GeminiExtension(Extension):
    def __init__(self):
        super().__init__()
        self.subscribe(KeywordQueryEvent, KeywordQueryEventListener())


class KeywordQueryEventListener(EventListener):
    def on_event(self, event, extension):
        query = event.get_argument() or ""
        api_key = extension.preferences.get("api_key") or ""
        model = extension.preferences.get("model") or "gemini-pro"
        wrap_length = int(extension.preferences.get("wrap_length")) or 5
        default_prompt = extension.preferences.get("default_prompt") or ""

        if not query or not api_key:
            result = ExtensionResultItem(
                icon="images/icon.png",
                name="Missing information",
                description="Please enter a question and set your API key in preferences",
                on_enter=HideWindowAction()
            )
            return RenderResultListAction([result])

        try:
            ai_answer = self.get_gemini_response(api_key, model, default_prompt, query)
        except Exception as e:
            result = ExtensionResultItem(
                icon="images/icon.png",
                name="An error occurred",
                description=str(e),
            )
            return RenderResultListAction([result])

        wrapped_lines = []
        current_line = ""
        for word in ai_answer.split():
            if len(current_line + word) <= wrap_length:
                current_line += " " + word
            else:
                wrapped_lines.append(current_line.strip())
                current_line = word
        wrapped_lines.append(current_line.strip())

        wrapped_answer = "\n".join(wrapped_lines)

        result = ExtensionResultItem(
            icon="images/icon.png",
            name=model.capitalize(),
            description=wrapped_answer,
            on_enter=CopyToClipboardAction(ai_answer)
        )

        return RenderResultListAction([result])

    def get_gemini_response(self, api_key, model, default_prompt, query):
        url = f"https://generativelanguage.googleapis.com/v1/models/{model}:generateContent"
        headers = {
            "Content-Type": "application/json"
        }
        
        # Add API key as a URL parameter
        url += f"?key={api_key}"
        
        # Construct the prompt including the default prompt if provided
        full_prompt = default_prompt + "\n\n" + query if default_prompt else query
        
        data = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": full_prompt
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 1024
            }
        }
        
        response = requests.post(url, headers=headers, data=json.dumps(data), timeout=60)
        response.raise_for_status()  # Raise exception for HTTP errors
        
        response_data = response.json()
        
        # Extract the text from the response
        try:
            text_response = response_data["candidates"][0]["content"]["parts"][0]["text"]
            return text_response
        except (KeyError, IndexError) as e:
            raise Exception(f"Failed to parse Gemini response: {str(e)}")


if __name__ == "__main__":
    GeminiExtension().run()
