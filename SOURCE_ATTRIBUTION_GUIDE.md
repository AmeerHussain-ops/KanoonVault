# Source Attribution System Implementation Guide

## Overview
KanoonVault now includes a comprehensive source attribution system where every AI response includes clickable source references, allowing users to access the original documents directly.

## Architecture

### 1. Database Schema
**Documents Table** stores complete file metadata:
- `id`: Unique document identifier
- `case_id`: Associated case
- `original_filename`: User-facing filename
- `stored_file_path`: Full path to file on disk
- `mime_type`: Document MIME type (pdf, image, text, etc.)
- `file_size`: Document size in bytes
- `uploaded_at`: Upload timestamp

**Text Chunks Table** stores both content and comprehensive source metadata:
- `source_metadata`: JSON string containing:
  - `document_id`: Reference to document
  - `original_file_name`: Filename
  - `page_number`: Page where chunk originated
  - `case_id`: Associated case
  - `upload_date`: When document was uploaded

### 2. Backend Pipeline

#### Retrieval System (vector_memory_service.py)
```python
retrieve_relevant_chunks(question, case_id, max_results=8)
# Returns: (context_string, source_metadata_list)
```
- Uses hybrid search (FTS + vector similarity)
- Returns both the text content AND complete source metadata
- Source metadata includes document IDs for direct file access

#### Special Command Detection (llm_service.py)
```python
is_special_command(question: str) -> bool
```
Detects file access requests:
- "show original file"
- "open pdf"
- "where is this written"
- "show source"
- "download document"
- "view original"
- "open document"
- "get file"

When detected, the system returns empty LLM response with metadata instead of generating an answer.

#### Streaming Response (llm_service.py)
```python
async def stream_response(question: str, case_id: int) -> AsyncIterator[Tuple[str, List[Dict]]]
```
- Yields tuples of (token, source_metadata)
- For special commands: yields ("", metadata) immediately
- For regular queries: yields LLM tokens with metadata attached to each token

#### Source Formatting (llm_service.py)
```python
format_source_references(source_metadata: List[Dict]) -> str
```
Formats sources in the pattern:
```
Sources:
[Document Name] — Page [123] — [DOC_ID:456]
[Another Document] — [DOC_ID:789]
```

The `[DOC_ID:N]` tags contain document IDs used for file serving.

### 3. API Endpoints

#### GET /documents/{document_id}/open
Serves documents for download/viewing:
- **Parameter**: `document_id` - Integer document ID
- **Returns**: Original file with appropriate MIME type
- **Example**: 
  ```
  GET /documents/42/open
  → Returns: case_file_2024.pdf with Content-Disposition: attachment
  ```

#### POST /chat/query
Enhanced to handle source attribution:
- **Request**: `{ question, case_id, stream: true }`
- **Response**: Server-Sent Events (SSE) stream
- **Stream Format**:
  ```
  data: token1
  data: token2
  data: ...
  data: 
  Sources:
  [Doc Name] — Page [123] — [DOC_ID:456]
  data: [DONE]
  ```

### 4. Frontend Integration (app.js)

#### Enhanced streamChat Function
```javascript
async function streamChat(question)
```
- Collects tokens from the server stream
- Separates content from source references
- Detects special command responses (URLs)
- Updates UI with both content and clickable source links

#### Source Link Rendering
The frontend converts source metadata into clickable links:
```javascript
// Pattern 1: With page numbers
[Document Name] — Page [123] — [DOC_ID:456]
↓ becomes ↓
<a href="/documents/456/open">Open File</a>

// Pattern 2: Without page numbers
[Document Name] — [DOC_ID:789]
↓ becomes ↓
<a href="/documents/789/open">Open File</a>
```

#### Special Command Handling
When user asks "show original file", the system:
1. Detects special command
2. Retrieves relevant document chunks
3. Returns file link instead of AI response
4. Frontend renders clickable link: `📄 Open File`

### 5. Styling (style.css)

New CSS classes for source attribution:
```css
.source-link {
    /* Container for source references */
    margin: 8px 0;
    padding: 8px 12px;
    background: var(--surface-2);
    border-left: 3px solid var(--accent-primary);
}

.file-link {
    /* Clickable file link styling */
    color: var(--accent-secondary);
    text-decoration: none;
    font-weight: 500;
}

.file-link:hover {
    background: var(--accent-secondary);
    color: var(--bg-primary);
}
```

## Workflow Example

### User Query: "What did the judge say?"
1. **Frontend**: Send question to `/chat/query`
2. **Backend**: 
   - Not a special command
   - Retrieve relevant chunks with source metadata
   - Stream LLM response with metadata attached
3. **Frontend**:
   - Display answer as it streams in
   - When complete, extract source metadata
   - Render clickable source links
4. **Display**:
   ```
   KanoonVault AI: The judge stated...
   
   Sources:
   [Judgment Order 2024] — Page [5] — [Open File]
   [Court Minutes] — Page [2] — [Open File]
   ```

### User Query: "Show me the original PDF"
1. **Frontend**: Send question to `/chat/query`
2. **Backend**:
   - Detects as special command
   - Retrieves relevant documents
   - Returns metadata with document IDs
3. **Frontend**:
   - Detects file link in response
   - Renders single clickable link
4. **Display**:
   ```
   📄 Open File
   ```
   (Clicking opens `/documents/42/open` which serves the actual file)

## Security Considerations

1. **File Access**:
   - Only documents already in the system can be accessed
   - File paths are validated before serving
   - MIME types are properly set for safe browser handling

2. **Source Attribution**:
   - System never invents source information
   - Only returns metadata from actual retrieved chunks
   - Works with hybrid search (FTS + vector) for reliability

3. **Special Commands**:
   - Whitelist of recognized commands
   - Prevents arbitrary file access requests
   - Falls back to normal AI response if pattern not recognized

## Implementation Checklist

- [x] Database schema updated for comprehensive metadata
- [x] Retrieval system returns both content and metadata
- [x] Special command detection implemented
- [x] Streaming response handles metadata tuples
- [x] Format source references function with document IDs
- [x] File serving endpoint (`/documents/{document_id}/open`)
- [x] Frontend source link rendering with regex patterns
- [x] CSS styling for source links and file links
- [x] Special command handling in frontend
- [x] Error handling for missing files

## Testing Recommendations

1. **Upload a document** and verify metadata storage
2. **Ask a question** and confirm sources appear in response
3. **Click source links** and verify files download correctly
4. **Try special commands** ("show original file", "open PDF")
5. **Test with multiple cases** to ensure isolation
6. **Check file types** (PDF, images, text) are served correctly

## Future Enhancements

- [ ] Add text highlighting for specific chunks from documents
- [ ] Support for direct annotation of documents
- [ ] Download multiple sources as ZIP
- [ ] Search within specific documents only
- [ ] Document preview in modal instead of download
- [ ] Version tracking for document updates
