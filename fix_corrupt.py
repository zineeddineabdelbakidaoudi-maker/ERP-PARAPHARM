with open('ui/pages/fiscal_pages.py', 'r', encoding='utf-8') as f:
    text = f.read()

# text looks like "éaébécé"
# We just need to take text[1::2] (start at 1, step 2)
# Wait, let's verify on a small string
# "abc".replace("", "é") -> 'éaébécé' (len 7)
# text[1::2] -> 'abc'
# Perfect!

restored = text[1::2]

# Let's restore the valid 'é's we had replaced. Wait, we don't need to! We are just stripping the injected ones. The valid 'é's were already in the original text, but they got flanked by injected 'é's.
# Example: original="é", replace("", "é") -> "ééé". text[1::2] -> "é". It preserves everything perfectly!

with open('ui/pages/fiscal_pages.py', 'w', encoding='utf-8') as f:
    f.write(restored)
