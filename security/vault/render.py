import html


def render_comment(author: str, text: str) -> str:
    """HTML for one comment. Author and text are user input, so both are escaped."""
    return f'<div class="comment"><b>{html.escape(author)}</b>: {html.escape(text)}</div>'
