# -*- coding: utf-8 -*-
import pymysql
import traceback
import sys
reload(sys)
sys.setdefaultencoding('utf-8')


# 数据库类
class Db:
    def __init__(self):
        self.conn = pymysql.connect(host='192.168.81.23',
                                    port=3306,
                                    user='keystone',
                                    password='OptValley@4312',
                                    db='keystone',
                                    charset='utf8mb4',
                                    cursorclass=pymysql.cursors.DictCursor)

    def query(self, sql, oneorall):
        try:
            cur = self.conn.cursor()
            cur.execute(sql)
            if oneorall == 1:
                results = cur.fetchone()    #查询一个
            else:
                results = cur.fetchall()    #查询所有
            self.conn.commit()
            cur.close()
            return results
        except:
            traceback.print_exc()
            self.conn.rollback()

    def close(self):
        self.conn.close()





