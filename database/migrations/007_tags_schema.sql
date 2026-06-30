/* Migration: 007_tags_schema.sql */
CREATE TABLE IF NOT EXISTS tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS knowledge_page_tags (
    knowledge_page_id INTEGER NOT NULL,
    tag_id INTEGER NOT NULL,
    PRIMARY KEY (knowledge_page_id, tag_id),
    CONSTRAINT fk_kp_tags_kp FOREIGN KEY (knowledge_page_id) REFERENCES knowledge_pages(id) ON DELETE CASCADE,
    CONSTRAINT fk_kp_tags_tag FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_tag_name ON tags(name);
