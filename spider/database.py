import sqlite3
import config
from datetime import datetime

class WeiboDatabase:
    def __init__(self):
        self.conn = sqlite3.connect(config.DB_PATH)
        self.cursor = self.conn.cursor()
        self.create_table()
    
    def create_table(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS weibo_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_name TEXT,
                content TEXT,
                likes INTEGER DEFAULT 0,
                comments INTEGER DEFAULT 0,
                reposts INTEGER DEFAULT 0,
                post_time TEXT,
                crawl_time TEXT,
                url TEXT
            )
        ''')
        self.conn.commit()
    
    def insert_post(self, user_name, content, likes, comments, reposts, post_time, url):
        crawl_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.cursor.execute('''
            INSERT INTO weibo_posts (user_name, content, likes, comments, reposts, post_time, crawl_time, url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_name, content, likes, comments, reposts, post_time, crawl_time, url))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def get_all_posts(self):
        self.cursor.execute('SELECT * FROM weibo_posts ORDER BY id DESC')
        return self.cursor.fetchall()
    
    def get_posts_paginated(self, page=1, page_size=100):
        """分页获取数据"""
        offset = (page - 1) * page_size
        self.cursor.execute('SELECT * FROM weibo_posts ORDER BY id DESC LIMIT ? OFFSET ?', 
                          (page_size, offset))
        return self.cursor.fetchall()
    
    def get_total_count(self):
        """获取总记录数"""
        self.cursor.execute('SELECT COUNT(*) FROM weibo_posts')
        return self.cursor.fetchone()[0]
    
    def search_posts(self, keyword):
        self.cursor.execute('SELECT * FROM weibo_posts WHERE content LIKE ? OR user_name LIKE ?', 
                          (f'%{keyword}%', f'%{keyword}%'))
        return self.cursor.fetchall()
    
    def update_post(self, post_id, user_name, content, likes, comments, reposts, post_time, url):
        self.cursor.execute('''
            UPDATE weibo_posts 
            SET user_name=?, content=?, likes=?, comments=?, reposts=?, post_time=?, url=?
            WHERE id=?
        ''', (user_name, content, likes, comments, reposts, post_time, url, post_id))
        self.conn.commit()
    
    def delete_post(self, post_id):
        self.cursor.execute('DELETE FROM weibo_posts WHERE id=?', (post_id,))
        self.conn.commit()
    
    def delete_all_posts(self):
        self.cursor.execute('DELETE FROM weibo_posts')
        self.conn.commit()
    
    def get_statistics(self):
        self.cursor.execute('SELECT COUNT(*), SUM(likes), SUM(comments), SUM(reposts) FROM weibo_posts')
        return self.cursor.fetchone()
    
    def close(self):
        self.conn.close()
