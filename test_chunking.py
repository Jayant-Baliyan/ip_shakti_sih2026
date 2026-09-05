text = 'This is a test sentence. ' * 50
print(f'Text length: {len(text)}')
chunk_size = 512
overlap = 50
min_chunk_size = 100
chunks = []
start = 0
while start < len(text):
    end = min(start + chunk_size, len(text))
    if end < len(text):
        search_start = max(start + chunk_size - 100, start)
        sentence_end = end
        for i in range(end - 1, search_start - 1, -1):
            if text[i] in '.!?':
                if i + 1 >= len(text) or text[i + 1] in ' \n\r\t':
                    sentence_end = i + 1
                    break
        end = sentence_end
    chunk_text = text[start:end].strip()
    if len(chunk_text) >= min_chunk_size:
        chunks.append(chunk_text)
    start = end - overlap
    if start >= len(text):
        break
print(f'Chunks: {len(chunks)}')
for i, chunk in enumerate(chunks[:3]):
    print(f'  {i}: {len(chunk)} chars')