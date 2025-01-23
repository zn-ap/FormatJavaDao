#!/usr/bin/env python3

import os
import re
import sys

def find_max_length(all_parts):
    """Find the maximum length of SQL parts and add 1."""
    max_len = 0
    for part in all_parts:
        # Remove any existing padding
        cleaned = re.sub(r'\s+$', '', part)
        max_len = max(max_len, len(cleaned))
    return max_len + 1

def pad_line(line, max_length):
    """Pad a line to the specified length with spaces."""
    # Remove any existing padding
    line = re.sub(r'\s+$', '', line)
    return line + " " * (max_length - len(line))

def is_sql_keyword(word):
    """Check if a word is a SQL keyword that should start a new line."""
    keywords = {
        'SELECT', 'FROM', 'WHERE', 'ORDER BY', 'GROUP BY', 'HAVING',
        'LIMIT', 'OFFSET', 'INSERT', 'UPDATE', 'DELETE', 'JOIN',
        'LEFT JOIN', 'RIGHT JOIN', 'INNER JOIN', 'VALUES', 'SET',
        'AND', 'OR', 'ON', 'INTO', 'COMMIT'
    }
    return word.upper() in keywords

def split_variables(text):
    """Split a comma-separated list of variables into separate lines."""
    # Remove any trailing comma
    text = text.rstrip(',')
    # Split by comma and clean each part
    parts = [part.strip() for part in text.split(',') if part.strip()]
    # Add comma back to all but the last part
    for i in range(len(parts) - 1):
        parts[i] = parts[i] + ","
    return parts

def get_base_indentation(line):
    """Extract the base indentation from a line of code."""
    match = re.match(r'^\s*', line)
    return match.group(0) if match else ""

def format_sql(sql_text, base_indent):
    """Format a SQL query with proper indentation and alignment."""
    # Clean up the input
    sql_text = re.sub(r'\s+', ' ', sql_text.strip())
    
    # Split on SQL keywords while preserving the keywords
    parts = []
    current_part = []
    words = sql_text.split()
    i = 0
    while i < len(words):
        # Check for two-word keywords
        if i < len(words) - 1:
            two_words = f"{words[i]} {words[i+1]}"
            if is_sql_keyword(two_words):
                if current_part:
                    parts.append(' '.join(current_part))
                    current_part = []
                parts.append(two_words)
                i += 2
                continue
        
        # Check single words
        if is_sql_keyword(words[i]):
            if current_part:
                parts.append(' '.join(current_part))
                current_part = []
            parts.append(words[i])
        else:
            current_part.append(words[i])
        i += 1
    
    if current_part:
        parts.append(' '.join(current_part))
    
    # Process each part, splitting variables where needed
    formatted_parts = []
    for part in parts:
        if is_sql_keyword(part):
            formatted_parts.append(part)
        elif ',' in part:  # Variable list
            variables = split_variables(part)
            formatted_parts.extend(["  " + var for var in variables])
        else:
            formatted_parts.append("  " + part)

    # Calculate the maximum length needed
    max_length = find_max_length(formatted_parts)
    
    # Build the final formatted lines with proper indentation
    formatted_lines = []
    indent_level = len(base_indent) + 16
    sql_indent = " " * indent_level
    
    for i, part in enumerate(formatted_parts):
        padded_line = pad_line(part, max_length)
        if i == 0:
            formatted_lines.append(f'{sql_indent}"{padded_line}"')
        else:
            formatted_lines.append(f'{sql_indent}+ "{padded_line}"')
    
    return formatted_lines

def process_file(file_path):
    """Process a single DAO file."""
    print(f"Processing file: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Updated pattern to include prepareBatch and commit
    sql_pattern = r'(?:createQuery|createUpdate|prepareBatch|commit)\(\s*"([^"]+(?:\s*"\s*\+\s*"[^"]+)*)"'
    
    def replace_sql(match):
        # Extract the SQL text
        sql_text = match.group(1)
        # Remove line continuations and extra whitespace
        sql_text = re.sub(r'"\s*\+\s*"', ' ', sql_text)
        
        # Find the original indentation
        original_line = match.group(0)
        base_indent = get_base_indentation(original_line)
        
        # Format the SQL
        formatted_lines = format_sql(sql_text, base_indent)
        if not formatted_lines:
            return match.group(0)
        
        # Join the lines
        formatted_sql = '\n'.join(formatted_lines)
        
        # Determine which method is being used
        method = 'createQuery'
        if 'createUpdate' in original_line:
            method = 'createUpdate'
        elif 'prepareBatch' in original_line:
            method = 'prepareBatch'
        elif 'commit' in original_line:
            method = 'commit'
            
        query_start = re.search(f'{method}\\(\\s*"', original_line).start()
        return original_line[:query_start] + f'{method}(\n{formatted_sql}'
    
    # Replace all SQL blocks in the file
    new_content = re.sub(sql_pattern, replace_sql, content, flags=re.DOTALL)
    
    # Write the updated content
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print(f"Updated {file_path}")

def main():
    """Find and process all DAO files in the current directory and subdirectories."""
    for root, _, files in os.walk('.'):
        for file in files:
            # Check for both "Dao.java" and "DAO.java" endings
            if file.endswith('Dao.java') or file.endswith('DAO.java'):
                file_path = os.path.join(root, file)
                try:
                    process_file(file_path)
                except Exception as e:
                    print(f"Error processing {file_path}: {e}", file=sys.stderr)

if __name__ == '__main__':
    main()
    print("DAO SQL formatting completed.")
