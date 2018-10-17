# -*- coding: utf-8 -*-
import traceback
import json
import sys
import os
import time
import shutil
import zipfile
import multiprocessing
from os.path import join
# from data import Db
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER
from reportlab.pdfgen.canvas import Canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph, Spacer, Frame, BaseDocTemplate, PageTemplate, PageBreak, \
    Table, TableStyle, Image
from reportlab.lib import colors, pagesizes
from reportlab.rl_config import defaultPageSize, verbose
from reportlab.lib.units import inch
from reportlab.platypus.tableofcontents import TableOfContents

reload(sys)
sys.setdefaultencoding('utf-8')

# 路径
path = os.path.abspath(os.path.dirname(__file__))   # 脚本当前所在目录
pdf_tmp = path + "/pdf_tmp"     # pdf临时文件目录
pic_tmp = path + '/tmp'     # 存放图片临时目录

phantomjs_path = path + '/phantomjs/bin/phantomjs'    # phantomjs 路径
js_path = path + '/js/exportImg.js'  # js路径
# 报告字体样式
######################################################################
# 导入中文字体
pdfmetrics.registerFont(TTFont('hei', path + '/Fonts/simhei.ttf'))
pdfmetrics.registerFont(TTFont('song', path + '/Fonts/simsun.ttc'))

# 设置宋体的粗体格式（黑体）
pdfmetrics.registerFontFamily('song', normal='song', bold='hei')
# 默认换行风格为中文换行
ParagraphStyle.defaults['wordWrap'] = "CJK"
# 段落（字体）格式
styles = getSampleStyleSheet()
PS = ParagraphStyle
# 目录字体
toc1 = PS(name='Title', parent=styles['Normal'], fontName='hei', textColor=colors.black,
          fontSize=16, leading=15.85, alignment=TA_CENTER, spaceAfter=6)
H1 = PS(fontName='hei', fontSize=12, name='TOCHeading1', leftIndent=24, firstLineIndent=-20, spaceBefore=0, leading=20)
H2 = PS(parent=H1, name='TOCHeading2', firstLineIndent=0)
H3 = PS(parent=H1, name='TOCHeading3', firstLineIndent=20)
# 标题字体
h1 = PS(fontName='hei', fontSize=14, name='TOCHeading1', spaceBefore=24, spaceAfter=18, leading=15.85)
h2 = PS(parent=h1, fontSize=13, name='TOCHeading2', spaceBefore=24, spaceAfter=6)
h3 = PS(parent=h1, fontSize=12, name='TOCHeading3', spaceBefore=12, spaceAfter=6)
# 正文字体
body = PS(name='Body', parent=styles['Normal'], fontName='song', fontSize=12, leading=20, wordWrap='CJK', firstLineIndent=25)
# 关于我们
about_us = PS(name='about_us', parent=body, firstLineIndent=0)
# 表格字体
table_text = PS(name='table_text', parent=styles['Normal'], fontName='hei', fontSize=11, leading=20, wordWrap='CJK')
table_text_center = PS(name='table_text_center', parent=table_text, alignment=1)
# 表名
table_name = PS(name='table_name', parent=table_text, fontSize=10.5, alignment=1, spaceBefore=24)
# 图名
figure_name = PS(name='figure_name', parent=table_text, fontSize=10.5, alignment=1, spaceAfter=6)
# 长度距离
top_margin = pagesizes.A4[1] - inch
bottom_margin = inch
left_margin = inch
right_margin = pagesizes.A4[0] - inch
frame_width = right_margin - left_margin
######################################################################
global start_timestamp  # 审计该时间戳以后的数据
global end_timestamp  # 审计该时间戳以前的数据


def _doNothing(canvas, doc):
    '''Dummy callback for onPage'''
    pass


# 第一页模板（封面）
def firstPages(c, doc):
    c.drawImage(path + '/Assets/cover_audit.png', 0, 0, width=595.275590551, height=841.88976378)


# 其他页模板（页面页脚）
def laterPages(c, doc):
    c.saveState()
    c.setFont('hei', 12)
    c.drawImage(path + '/Assets/logo.jpg', 80, top_margin, width=80, height=64)
    c.drawString(right_margin - 152, top_margin + 10, "北京天地和兴科技有限公司")
    c.line(left_margin, top_margin, right_margin, top_margin)
    c.line(left_margin, bottom_margin, right_margin, bottom_margin)
    c.drawString(6 * inch, 0.75 * inch, "第 %d 页" % doc.page)
    c.restoreState()


# 审计依据
def evidence_table(story):
    evidence_data = [['《中华人民共和国网络安全法》'],
                     ['《中华人民共和国计算机信息系统安全保护条例》'],
                     ['《信息安全等级保护管理办法》'],
                     ['《计算机信息系统安全保护等级划分准则》'],
                     ['《信息系统安全等级保护定级指南》'],
                     ['《信息系统安全等级保护基本要求》'],
                     ['《信息系统安全等级保护测评准则》'],
                     ]
    evidence_t = Table(evidence_data, colWidths=439, rowHeights=25, spaceAfter=6)
    evidence_t.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'hei'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('BACKGROUND', (0, 0), (-1, 0), HexColor(0x31bbf2)),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor(0x2a323b)),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(Paragraph("表 <seq template='2.%(Chart2No+)s'/> WEB安全检测依据", table_name))
    story.append(evidence_t)


# 添加标题
def add_title(story, title, style):
    story.append(Paragraph(title, style))


# 关于我们
def about_us_3(story):
    add_title(story, '3 关于我们', h1)
    story.append(Paragraph('本报告由“工控安全审计平台”生成，是北京天地和兴科技有限公司研发的主机安全审计工具。'
                           '北京天地和兴科技有限公司永久保留本报告的解释权。', body))
    story.append(Paragraph('北京天地和兴科技有限公司感谢您对我们的信任和支持。', body))
    add_title(story, '3.1 联系我们', h2)
    story.append(Paragraph('•<b>电话:</b>' + '010-82896289', about_us))
    story.append(Paragraph('•<b>邮箱:</b>' + 'tdhx@tdhxkj.com', about_us))
    story.append(Paragraph('•<b>网址:</b>' + 'http://www.tdhxkj.com/', about_us))
    story.append(Paragraph('•<b>地址:</b>' + '北京市海淀区中关村科技园8号 华夏科技大厦三层', about_us))

# 安全级别说明图
def security_figure(story):
    story.append(Image(path + '/Assets/level.png', width=439, height=203))
    story.append(Paragraph("图 <seq template='2.%(Figure2No+)s'/> 安全级别说明", figure_name))


# 时间转时间戳
def time_to_timestamp(date_time):
    # 转换成时间数组
    timeArray = time.strptime(date_time, "%Y-%m-%d %H:%M:%S")
    # 转换成时间戳
    timestamp = time.mktime(timeArray)
    return timestamp


# 自定义模板类
class MyDocTemplate(BaseDocTemplate):
    def __init__(self, filename, **kw):
        """
        :rtype: object
        """
        self.allowSplitting = 0
        BaseDocTemplate.__init__(self, filename,  **kw)
        # template = PageTemplate('normal', [Frame(2.5*cm, 2.5*cm, 15*cm, 25*cm, id='F1')])
        # self.addPageTemplates(template)

    def afterFlowable(self, flowable):
        "Registers TOC entries."
        if flowable.__class__.__name__ == 'Paragraph':
            text = flowable.getPlainText()
            style = flowable.style.name
            if style == 'TOCHeading1':
                key = 'h1-%s' % self.seq.nextf('TOCHeading1')
                self.canv.bookmarkPage(key)
                self.canv.addOutlineEntry(text, key, 0, 0)
                self.notify('TOCEntry', (0, text, self.page, key))
            if style == 'TOCHeading2':
                key = 'h2-%s' % self.seq.nextf('TOCHeading2')
                self.canv.bookmarkPage(key)
                self.canv.addOutlineEntry(text, key, 1, 0)
                self.notify('TOCEntry', (1, text, self.page, key))
            if style == 'TOCHeading3':
                key = 'h3-%s' % self.seq.nextf('TOCHeading3')
                self.canv.bookmarkPage(key)
                self.canv.addOutlineEntry(text, key, 2, 0)
                self.notify('TOCEntry', (2, text, self.page, key))
            if style == 'TOCHeading4':
                key = 'h4-%s' % self.seq.nextf('TOCHeading4')
                self.canv.bookmarkPage(key)
                self.canv.addOutlineEntry(text, key, 3, 0)
                self.notify('TOCEntry', (3, text, self.page, key))

    def handle_pageBegin(self):
        '''override base method to add a change of page template after the firstpage.
        '''
        self._handle_pageBegin()
        self._handle_nextPageTemplate('Later')

    def build(self, flowables, onFirstPage=_doNothing, onLaterPages=_doNothing, canvasmaker=Canvas):
        """build the document using the flowables.  Annotate the first page using the onFirstPage
               function and later pages using the onLaterPages function.  The onXXX pages should follow
               the signature

                  def myOnFirstPage(canvas, document):
                      # do annotations and modify the document
                      ...

               The functions can do things like draw logos, page numbers,
               footers, etcetera. They can use external variables to vary
               the look (for example providing page numbering or section names).
        """
        self._calc()    #in case we changed margins sizes etc
        frameT = Frame(self.leftMargin, self.bottomMargin, self.width, self.height, id='normal')
        self.addPageTemplates([PageTemplate(id='First',frames=frameT, onPage=onFirstPage,pagesize=self.pagesize),
                        PageTemplate(id='Later',frames=frameT, onPage=onLaterPages,pagesize=self.pagesize)])
        if onFirstPage is _doNothing and hasattr(self,'onFirstPage'):
            self.pageTemplates[0].beforeDrawPage = self.onFirstPage
        if onLaterPages is _doNothing and hasattr(self,'onLaterPages'):
            self.pageTemplates[1].beforeDrawPage = self.onLaterPages
        BaseDocTemplate.build(self,flowables, canvasmaker=canvasmaker)

    def multiBuild(self, story, onFirstPage=_doNothing, onLaterPages=_doNothing, canvasmaker=Canvas, maxPasses=10, **buildKwds):
        """Makes multiple passes until all indexing flowables
        are happy.

        Returns number of passes"""
        self._calc()    # in case we changed margins sizes etc
        frameT = Frame(self.leftMargin, self.bottomMargin, self.width, self.height, id='normal')

        self.addPageTemplates([PageTemplate(id='First', frames=frameT, onPage=onFirstPage, pagesize=pagesizes.A4),
                               PageTemplate(id='Later', frames=frameT, onPage=onLaterPages, pagesize=pagesizes.A4)])
        if onFirstPage is _doNothing and hasattr(self, 'onFirstPage'):
            self.pageTemplates[0].beforeDrawPage = self.onFirstPage
        if onLaterPages is _doNothing and hasattr(self, 'onLaterPages'):
            self.pageTemplates[1].beforeDrawPage = self.onLaterPages
        self._indexingFlowables = []
        # scan the story and keep a copy
        for thing in story:
            if thing.isIndexing():
                self._indexingFlowables.append(thing)

        # better fix for filename is a 'file' problem
        self._doSave = 0
        passes = 0
        mbe = []
        self._multiBuildEdits = mbe.append
        while 1:
            passes += 1
            if self._onProgress:
                self._onProgress('PASS', passes)
            if verbose: sys.stdout.write('building pass '+str(passes) + '...')

            for fl in self._indexingFlowables:
                fl.beforeBuild()

            # work with a copy of the story, since it is consumed
            tempStory = story[:]
            self.build(tempStory, **buildKwds)
            # self.notify('debug',None)

            for fl in self._indexingFlowables:
                fl.afterBuild()

            happy = self._allSatisfied()

            if happy:
                self._doSave = 0
                self.canv.save()
                break
            if passes > maxPasses:
                raise IndexError("Index entries not resolved after %d passes" % maxPasses)

            # work through any edits
            while mbe:
                e = mbe.pop(0)
                e[0](*e[1:])

        del self._multiBuildEdits
        if verbose:
            print('saved')
        return passes


# 总览报告
class Overview:
    def __init__(self, start_time, end_time):
        # self.db = Db()  # 连接数据库
        self.grade = '高危'
        self.grade_color = HexColor(0xe20c1e)   # 等级颜色
        self.id = None  # 报告id
        self.name = None  # 任务名称
        self.high = 5   # 病毒木马数量
        self.medium = 6  # 程序告警数量 + 设备告警数量
        self.low = 7    # 操作告警数量
        self.alm = 0    # 程序告警数量
        self.dev = 0    # 设备告警数量
        self.total = 0  # 总数
        self.h_list_id = []  # 主机列表 id
        self.alm_dict = dict()  # 主机ID:程序告警数量
        self.virus_dict = dict()  # 主机ID:病毒木马数量
        self.dev_dict = dict()  # 主机ID:设备告警数量
        self.act_dict = dict()  # 主机ID:操作告警数量
        self.assets_dict = dict()   # 主机ID:全部告警数量
        self.server_dict = dict()   # 主机id:主机名称
        self.start_time = start_time  # 开始时间
        self.end_time = end_time  # 结束时间
        self.src_dst = [["192.168.81.135<--->192.168.81.24", "SNMP", "3", "10%"],
                        ["192.168.81.135<--->192.168.81.24", "SNMP", "3", "10%"],
                        ["192.168.81.135<--->192.168.81.24", "SNMP", "3", "10%"],
                        ["192.168.81.135<--->192.168.81.24", "SNMP", "3", "10%"],
                        ["192.168.81.135<--->192.168.81.24", "SNMP", "3", "10%"]]
        self.proto_time_data = {"time": ['00:00', '01:00', '02:00', '03:00', '04:00', '05:00', '06:00', '07:00', '08:00', '09:00', '10:00', '11:00', '12:00', '13:00', '14:00', '15:00', '16:00', '17:00', '18:00', '19:00', '20:00', '21:00', '22:00', '23:00'],
                           "all": [26, 20, 26, 26, 26, 16, 26, 26, 30, 26, 26, 26, 26, 34, 26, 26, 26, 23, 26, 26, 26, 26, 26, 26]}

    # 统计病毒木马、告警数量
    def stats_info(self):
        virus_sql = "select count(*) from en_server_threaten_log where (unix_timestamp(cdate) between " + \
              str(start_timestamp) + " and " + str(end_timestamp) + ") and detail!=''"
        virus_result = self.db.query(virus_sql, 1)

        alm_sql = "select count(*) from en_server_threaten_log where (unix_timestamp(cdate) between " + \
              str(start_timestamp) + " and " + str(end_timestamp) + ") and detail=''"
        alm_result = self.db.query(alm_sql, 1)

        act_sql = "select count(*) from en_server_option_warn_log where (unix_timestamp(cdate) between " + \
              str(start_timestamp) + " and " + str(end_timestamp) + ")"
        act_result = self.db.query(act_sql, 1)

        dev_sql = "select count(*) from en_server_device_warn_log where (unix_timestamp(cdate) between " + \
              str(start_timestamp) + " and " + str(end_timestamp) + ")"
        dev_result = self.db.query(dev_sql, 1)

        self.high = virus_result['count(*)']
        self.medium = alm_result['count(*)'] + dev_result['count(*)']
        self.low = act_result['count(*)']
        self.dev = dev_result['count(*)']
        self.alm = alm_result['count(*)']
        self.total = self.high + self. medium + self.low
        # 为了防止除0错误，暂且在这里将self.total 设置为-1
        self.total=self.total if self.total else -1
        # return [virus_result['count(*)'], alm_result['count(*)'], act_result['count(*)'], dev_result['count(*)']]

    # 总体评价图
    def level_figure(self, story):
        self.stats_info()
        if self.high > 0:
            score = 20 - self.high
            if score <= 0:
                score = 0
        elif self.medium > 0:
            score = 70 - self.medium
            self.grade = '中危'
            self.grade_color = HexColor(0xfa7800)
            if score <= 21:
                score = 21
        elif self.low > 0:
            score = 100 - self.low
            self.grade = '低危'
            self.grade_color = HexColor(0xf4df1f)
            if score <= 71:
                score = 71
        else:
            self.grade = '安全'
            self.grade_color = HexColor(0x31bbf2)
            score = 100
        json_string = json.dumps({'percent': score, 'delta': 20})
        cmd = phantomjs_path + ' ' + js_path + ' -url ' + path + '/js/charts/tpl/index_text_3.html -width 320 -height' \
                                                                 ' 335 -json ' + "'" + json_string + "' -outfile " + path + "/tmp/3.png"
        sys.stderr.write("start cmd:"+cmd)
        os.system(cmd)
        sys.stderr.write("end cmd:" + cmd)
        story.append(Image(path + '/tmp/3.png', width=200, height=209.375))
        sys.stderr.write("end Image(3.png)")
        story.append(Paragraph("图 <seq template='2.%(Figure2No+)s'/> 总体评价", figure_name))

    # 资产清点图
    def assets_figure(self, story):
        alm_result = self.db.query("select server_id from en_server_threaten_log where (unix_timestamp(cdate)"
                                       "between " + str(start_timestamp) + " and " +
                                       str(end_timestamp) + ") and detail=''", 0)
        for i in alm_result:
            if i['server_id'] not in self.alm_dict:
                self.alm_dict[i['server_id']] = 1
            else:
                self.alm_dict[i['server_id']] += 1
            if i['server_id'] not in self.assets_dict:
                self.assets_dict[i['server_id']] = 1
            else:
                self.assets_dict[i['server_id']] += 1

        virus_result = self.db.query("select server_id from en_server_threaten_log where (unix_timestamp(cdate)"
                                   "between " + str(start_timestamp) + " and " +
                                   str(end_timestamp) + ") and detail!=''", 0)
        for i in virus_result:
            if i['server_id'] not in self.virus_dict:
                self.virus_dict[i['server_id']] = 1
            else:
                self.virus_dict[i['server_id']] += 1
            if i['server_id'] not in self.assets_dict:
                self.assets_dict[i['server_id']] = 1
            else:
                self.assets_dict[i['server_id']] += 1

        dev_result = self.db.query("select server_id from en_server_device_warn_log where (unix_timestamp(cdate)"
                                   "between " + str(start_timestamp) + " and " +
                                   str(end_timestamp) + ")", 0)
        for i in dev_result:
            if i['server_id'] not in self.dev_dict:
                self.dev_dict[i['server_id']] = 1
            else:
                self.dev_dict[i['server_id']] += 1
            if i['server_id'] not in self.assets_dict:
                self.assets_dict[i['server_id']] = 1
            else:
                self.assets_dict[i['server_id']] += 1

        act_result = self.db.query("select server_id from en_server_option_warn_log where (unix_timestamp(cdate)"
                                   "between " + str(start_timestamp) + " and " +
                                   str(end_timestamp) + ")", 0)
        for i in act_result:
            if i['server_id'] not in self.act_dict:
                self.act_dict[i['server_id']] = 1
            else:
                self.act_dict[i['server_id']] += 1
            if i['server_id'] not in self.assets_dict:
                self.assets_dict[i['server_id']] = 1
            else:
                self.assets_dict[i['server_id']] += 1

        self.assets_dict = sorted(self.assets_dict.items(), key=lambda buff: buff[1])[:12]
        xAxis = list()
        series = list()
        for i in self.assets_dict:
            xAxis.append(i[0])
            series.append(i[1])
        json_dict = {"xAxis": xAxis, "series": series}
        json_string = json.dumps(json_dict)

        cmd = phantomjs_path + ' ' + js_path + ' -url ' + path + '/js/charts/tpl/resourceDetail.html  -width 800 ' \
                                               '-height 400 -json ' + "'" + json_string + "' -outfile " + path + \
                                               "/tmp/resourceDetail.png"
        os.system(cmd)
        story.append(Image(path + '/tmp/resourceDetail.png', width=439, height=219.5))
        story.append(Paragraph("图 <seq template='2.%(Figure3No+)s'/> 主机清点", figure_name))

    # 高中低表格
    def risk_stats_table(self, story):
        data = [['等级', '个数', '比例'],
                ['高危', self.high, '%.2f%%' % ((self.high / float(self.total) if self.total!=0 else 0) * 100)],
                ['中危', self.medium, '%.2f%%' % ((self.medium / float(self.total) if self.total !=0 else 0) * 100)],
                ['低危', self.low,  '%.2f%%' % ((self.low / float(self.total) if self.total !=0 else 0 ) * 100)]
                ]
        t = Table(data, colWidths=[146, 147, 146], rowHeights=25, spaceAfter=6)
        t.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'hei'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('BACKGROUND', (0, 0), (-1, 0), HexColor(0x31bbf2)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('TEXTCOLOR', (0, 1), (0, 1), HexColor(0xe20c1e)),
            ('TEXTCOLOR', (0, 2), (0, 2), HexColor(0xfa7800)),
            ('TEXTCOLOR', (0, 3), (0, 3), HexColor(0xf4df1f)),
            ('GRID', (0, 0), (-1, -1), 0.5, HexColor(0x2a323b)),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(Paragraph("表 <seq template='3.%(Chart3No+)s'/> 风险比例详情", table_name))
        story.append(t)

    # 高中低环形图
    def risk_figure(self, story):
        json_string = "{\"low\":" + str(self.high) + \
                      ",\"mid\":" + str(self.medium) +\
                      ",\"high\":" + str(self.low) + "}"
        cmd = phantomjs_path + ' ' + js_path + ' -url ' + \
              path + '/js/charts/tpl/index_text_1.html -width 500 -height 390 -json ' + "'" + \
              json_string + "' -outfile " + path + "/tmp/1.png"
        os.system(cmd)
        story.append(Image(path + '/tmp/1.png', width=400, height=312))
        story.append(Paragraph("图 <seq template='3.%(Figure3No+)s'/> 风险等级分布", figure_name))

    # 等级柱状图
    def risk_type_figure(self, story):
        json_string = "{\"low\":" + '%.2f' % (self.high / float(self.total) * 100) + \
                      ",\"mid\":" + '%.2f' % (self.medium / float(self.total) * 100) +\
                      ",\"high\":" + '%.2f' % (self.low / float(self.total) * 100) + "}"
        cmd = phantomjs_path + ' ' + js_path + ' -url ' + path + '/js/charts/tpl/index_text_0.html -width 400 -height' \
                                                ' 360 -json ' + "'" + json_string + "' -outfile " + path + "/tmp/0.png"
        os.system(cmd)
        story.append(Image(path + '/tmp/0.png', width=400, height=360))
        story.append(Paragraph("图 <seq template='3.%(Figure3No+)s'/> 风险等级分布", figure_name))

    # 风险类型表格
    def type_stats_table(self, story):
        data = [['风险类型', '高危', '中危', '低危'],
                ['病毒木马', self.high, 0, 0],
                ['程序告警', 0, self.alm, 0],
                ['操作告警', 0, self.low, 0],
                ['设备告警', 0, 0, self.dev]
                ]

        t = Table(data, colWidths=[139, 100, 100, 100], rowHeights=25, spaceAfter=6)
        t.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'hei'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('BACKGROUND', (0, 0), (-1, 0), HexColor(0x31bbf2)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.5, HexColor(0x2a323b)),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(Paragraph("表 <seq template='3.%(Chart3No+)s'/> 风险类型详情", table_name))
        story.append(t)

    # 风险类型图
    def type_figure(self, story):
        json_string = json.dumps({'title': ['设备告警', '操作告警', '程序告警', '病毒木马'],
                                  'num': [self.dev, self.low, self.alm, self.high]})
        cmd = phantomjs_path + ' ' + js_path + ' -url ' + path + '/js/charts/tpl/index_text_2.html -width 600 -height' \
                                                ' 320 -json ' + "'" + json_string + "' -outfile " + path + "/tmp/2.png"
        os.system(cmd)
        story.append(Image(path + '/tmp/2.png', width=439, height=234.1))
        story.append(Paragraph("图 <seq template='3.%(Figure3No+)s'/> 风险类型分布", figure_name))

    # 病毒木马趋势图
    def virus_figure(self, story):
        sql = "select virus,year,month,day  from en_servers_option_warn_counter where hour=0 and month!=0 and " \
              "day!=0"
        result = self.db.query(sql, 0)
        xAxis = list()
        series = list()
        for i in result:
            time_str = str(i['year']) + "-" + str(i['month']) + "-" + str(i['day']) + ' 00:00:00'
            if start_timestamp <= time_to_timestamp(time_str) <= end_timestamp:
                xAxis.append(str(i['year']) + str(i['month']) + str(i['day']))
                series.append(i['virus'])
        json_dict = {"xAxis": xAxis, "series": series}
        json_string = json.dumps(json_dict)
        cmd = phantomjs_path + ' ' + js_path + ' -url ' + path + '/js/charts/tpl/summaryVirus.html  -width 800 ' \
                                               '-height 400 -json ' + "'" + json_string + "' -outfile " + path + \
                                               "/tmp/overview_summaryVirus.png"
        os.system(cmd)
        story.append(Image(path + '/tmp/overview_summaryVirus.png', width=439, height=219.5))
        story.append(Paragraph("图 <seq template='3.%(Figure3No+)s'/> 病毒木马趋势图", figure_name))

    # 程序告警趋势图
    def alm_figure(self, story):
        sql = "select program,year,month,day  from en_servers_option_warn_counter where hour=0 and month!=0 and " \
              "day!=0"
        result = self.db.query(sql, 0)
        xAxis = list()
        series = list()
        for i in result:
            time_str = str(i['year']) + "-" + str(i['month']) + "-" + str(i['day']) + ' 00:00:00'
            if start_timestamp <= time_to_timestamp(time_str) <= end_timestamp:
                xAxis.append(str(i['year']) + str(i['month']) + str(i['day']))
                series.append(i['program'])
        json_dict = {"xAxis": xAxis, "series": series}
        json_string = json.dumps(json_dict)
        cmd = phantomjs_path + ' ' + js_path + ' -url ' + path + '/js/charts/tpl/summaryProgramWarn.html  -width 800 ' \
                                               '-height 400 -json ' + "'" + json_string + "' -outfile " + path + \
                                               "/tmp/overview_summaryProgramWarn.png"
        os.system(cmd)
        story.append(Image(path + '/tmp/overview_summaryProgramWarn.png', width=439, height=219.5))
        story.append(Paragraph("图 <seq template='3.%(Figure3No+)s'/> 程序告警趋势图", figure_name))

    # 操作告警图
    def action_figure(self, story):
        sql = "select count(*) from en_server_option_warn_log where (unix_timestamp(cdate) " \
              "between " + str(start_timestamp) + " and " + \
              str(end_timestamp) + ") and type='" + '危险操作' + "'"
        danger_result = self.db.query(sql, 1)
        danger = danger_result['count(*)']

        permission_result = self.db.query("select count(*) from en_server_option_warn_log where (unix_timestamp(cdate) "
                                       "between " + str(start_timestamp) + " and " +
                                       str(end_timestamp) + ") and type='用户权限变更'", 1)
        permission = permission_result['count(*)']

        file_result = self.db.query("select count(*) from en_server_option_warn_log where (unix_timestamp(cdate) "
                                       "between " + str(start_timestamp) + " and " +
                                       str(end_timestamp) + ") and type='关键文件变更'", 1)
        file = file_result['count(*)']

        lock_result = self.db.query("select count(*) from en_server_option_warn_log where (unix_timestamp(cdate) "
                                       "between " + str(start_timestamp) + " and " +
                                       str(end_timestamp) + ") and type='用户登录失败超过阈值'", 1)
        lock = lock_result['count(*)']

        connection_result = self.db.query("select count(*) from en_server_option_warn_log where (unix_timestamp(cdate) "
                                       "between " + str(start_timestamp) + " and " +
                                       str(end_timestamp) + ") and type='网络外联事件'", 1)
        connection = connection_result['count(*)']

        login_result = self.db.query("select count(*) from en_server_option_warn_log where (unix_timestamp(cdate) "
                                       "between " + str(start_timestamp) + " and " +
                                       str(end_timestamp) + ") and type='用户登录事件'", 1)
        login = login_result['count(*)']

        act_dict = {"Data": [
            {"value": danger, "name": '危险操作'},
            {"value": permission, "name": '用户权限变更'},
            {"value": file, "name": '关键文件变更'},
            {"value": lock, "name": '用户登录失败超过阈值'},
            {"value": connection, "name": '网络外联事件'},
            {"value": login, "name": '用户登录事件'}
        ]}

        json_string = json.dumps(act_dict)

        cmd = phantomjs_path + ' ' + js_path + ' -url ' + path + '/js/charts/tpl/operationWarn.html  -width 600 ' \
                                               '-height 500 -json ' + "'" + json_string + "' -outfile " + path + \
                                               "/tmp/operationWarn.png"
        os.system(cmd)
        story.append(Image(path + '/tmp/operationWarn.png', width=439, height=365.8))
        story.append(Paragraph("图 <seq template='3.%(Figure3No+)s'/> 操作告警分布", figure_name))

    # 设备告警图
    def device_figure(self, story):
        usb_result = self.db.query("select count(*) from en_server_device_warn_log where (unix_timestamp(cdate) "
              "between " + str(start_timestamp) + " and " +
              str(end_timestamp) + ") and type='" + 'usb' + "'", 1)
        usb = usb_result['count(*)']

        cd_result = self.db.query("select count(*) from en_server_device_warn_log where (unix_timestamp(cdate) "
                                       "between " + str(start_timestamp) + " and " +
                                       str(end_timestamp) + ") and type='cd'", 1)
        cd = cd_result['count(*)']

        net_result = self.db.query("select count(*) from en_server_device_warn_log where (unix_timestamp(cdate) "
                                       "between " + str(start_timestamp) + " and " +
                                       str(end_timestamp) + ") and type='net'", 1)
        net = net_result['count(*)']

        port_result = self.db.query("select count(*) from en_server_device_warn_log where (unix_timestamp(cdate) "
                                       "between " + str(start_timestamp) + " and " +
                                       str(end_timestamp) + ") and type='port'", 1)
        port = port_result['count(*)']

        dev_dict = {"Data": [
            {"value": cd, "name": '光驱挂载和卸载'},
            {"value": port, "name": '串口、并口占用和释放'},
            {"value": net, "name": '网络设备启用/禁止'},
            {"value": usb, "name": 'USB设备插入/拔出'}
        ]}

        json_string = json.dumps(dev_dict)

        cmd = phantomjs_path + ' ' + js_path + ' -url ' + path + '/js/charts/tpl/deviceWarn.html  -width 600 ' \
                                               '-height 500 -json ' + "'" + json_string + "' -outfile " + path + \
                                               "/tmp/deviceWarn.png"
        os.system(cmd)
        story.append(Image(path + '/tmp/deviceWarn.png', width=439, height=365.8))
        story.append(Paragraph("图 <seq template='3.%(Figure3No+)s'/> 设备告警分布", figure_name))

    # 基本信息表格
    def base_info_table(self, story):
        # 表格数据
        base_info_data = [['选项', '内容'], ['开始时间', self.start_time], ['结束时间', self.end_time]]
        # sql = "select id, name, ip from en_server_list WHERE id IN " + str(tuple(self.h_list_id))
        # result = self.db.query(sql, 0)
        # for i in result:
        #     base_info_data.append([i['name'], i['ip']])
        #     self.server_dict[i['id']] = i['name']
        # 创建表格对象
        base_infor_t = Table(base_info_data, colWidths=[189, 250], rowHeights=25, spaceAfter=6)
        # 设置表格样式
        base_infor_t.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'hei'),  # 字体
            ('FONTSIZE', (0, 0), (-1, -1), 11),  # 字体大小
            ('BACKGROUND', (0, 0), (-1, 0), HexColor(0x31bbf2)),  # 第一列背景颜色
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),  # 表格第一列内文字颜色
            ('GRID', (0, 0), (-1, -1), 0.5, HexColor(0x2a323b)),  # 表格框线
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),  # 对齐
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # 对齐
        ]))
        story.append(Paragraph("表 <seq template='1.%(Chart1No+)s'/> 用户选择参数", table_name))
        story.append(base_infor_t)

    # 协议类型分布饼状图
    def proto_figure(self, story):
        json_string = "{\"modbus\":" + str(self.low) + \
                      ",\"s7\":" + str(self.medium) + \
                      ",\"s7plus\":" + str(self.low) + "}"
        cmd = phantomjs_path + ' ' + js_path + ' -url ' + \
              path + '/js/charts/tpl/index_proto_1.html -width 500 -height 390 -json ' + "'" + \
              json_string + "' -outfile " + path + "/tmp/1.png"
        # cmd = phantomjs_path + ' ' + js_path + ' -url ' + \
        #       path + '/js/charts/tpl/index_text_1.html -width 500 -height 390 ' + " -outfile " + path + "/tmp/1.png"
        os.system(cmd)
        story.append(Image(path + '/tmp/1.png', width=400, height=312))
        story.append(Paragraph("图 <seq template='2.%(Figure3No+)s'/> 协议类型分布图", figure_name))

    # 源地址-目的地址分布排行
    def src_dst_table(self, story):
        data = [['源地址-目的地址', '协议类型', '流条数', '比例'],
                [self.src_dst[0][0], self.src_dst[0][1], self.src_dst[0][2], self.src_dst[0][3]],
                [self.src_dst[0][0], self.src_dst[0][1], self.src_dst[0][2], self.src_dst[0][3]],
                [self.src_dst[0][0], self.src_dst[0][1], self.src_dst[0][2], self.src_dst[0][3]],
                [self.src_dst[0][0], self.src_dst[0][1], self.src_dst[0][2], self.src_dst[0][3]],
                [self.src_dst[0][0], self.src_dst[0][1], self.src_dst[0][2], self.src_dst[0][3]]
                ]

        t = Table(data, colWidths=[239, 100, 50, 50], rowHeights=25, spaceAfter=6)
        t.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'hei'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('BACKGROUND', (0, 0), (-1, 0), HexColor(0x31bbf2)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.5, HexColor(0x2a323b)),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(Paragraph("表 <seq template='2.%(Chart3No+)s'/> 源地址-目的地址分布排行", table_name))
        story.append(t)

    # 协议时间分布趋势图
    def proto_time(self, story):
        # sql = "select virus,year,month,day  from en_servers_option_warn_counter where hour=0 and month!=0 and " \
        #       "day!=0"
        # result = self.db.query(sql, 0)
        xAxis = list()
        series = list()
        for i in range(len(self.proto_time_data["time"])):
            xAxis.append(self.proto_time_data["time"][i])
            series.append(self.proto_time_data["all"][i])
        json_dict = {"xAxis": xAxis, "series": series}
        json_string = json.dumps(json_dict)
        cmd = phantomjs_path + ' ' + js_path + ' -url ' + path + '/js/charts/tpl/index_proto_2.html  -width 800 ' \
                                               '-height 400 -json ' + "'" + json_string + "' -outfile " + path + \
                                               "/tmp/proto_time.png"
        os.system(cmd)
        story.append(Image(path + '/tmp/proto_time.png', width=439, height=219.5))
        story.append(Paragraph("图 <seq template='2.%(Figure3No+)s'/> 协议时间分布趋势图", figure_name))

    # 传输层协议分布饼状图
    def l2_figure(self, story):
        json_string = "{\"TCP\":" + str(self.low) + \
                      ",\"UDP\":" + str(self.medium) + \
                      ",\"GOOSE\":" + str(self.high) + "}"
        cmd = phantomjs_path + ' ' + js_path + ' -url ' + \
              path + '/js/charts/tpl/index_proto_3.html -width 500 -height 390 -json ' + "'" + \
              json_string + "' -outfile " + path + "/tmp/1.png"
        # cmd = phantomjs_path + ' ' + js_path + ' -url ' + \
        #       path + '/js/charts/tpl/index_text_1.html -width 500 -height 390 ' + " -outfile " + path + "/tmp/1.png"
        os.system(cmd)
        story.append(Image(path + '/tmp/1.png', width=400, height=312))
        story.append(Paragraph("图 <seq template='2.%(Figure3No+)s'/> 协议类型分布图", figure_name))

    # 开始绘制协议审计报告
    def proto_go(self):
        story = list()  # 报告内容存储结构
        story.append(PageBreak())
        # 目录
        toc = TableOfContents()
        toc.dotsMinLevel = 0
        toc.levelStyles = [H1, H2, H3]
        story.append(Paragraph('目录', toc1))
        story.append(toc)
        # 分页
        story.append(PageBreak())
        add_title(story, '1 前言', h1)
        add_title(story, '1.1 报告阅读说明', h2)
        story.append(Paragraph('本报告是协议审计情况的统计，主要内容包含协议类型分布，TOP特征值展示，协议数随时间分布趋势，'
                               '以及传输层协议的分布。', body))
        story.append(Paragraph('北京天地和兴科技有限公司感谢您对我们的信任和支持。现将安全审计报告呈上。', body))
        add_title(story, '1.2 目标参数', h2)
        self.base_info_table(story)
        story.append(PageBreak())
        story.append(Paragraph('2 审计概述', h1))
        add_title(story, '2.1 协议类型分布图', h2)
        self.proto_figure(story)
        add_title(story, '2.2 源地址-目的地址top5', h2)
        self.src_dst_table(story)
        add_title(story, '2.3 协议时间分布趋势图', h2)
        self.proto_time(story)
        add_title(story, '2.4 传输层分布', h2)
        self.l2_figure(story)
        # self.risk_stats_table(story)
        # self.risk_type_figure(story)
        # add_title(story, '3.2.3 风险类型分布', h3)
        # self.type_figure(story)
        # self.type_stats_table(story)
        # add_title(story, '3.3.1 病毒木马', h3)
        # self.virus_figure(story)
        # add_title(story, '3.3.2 程序告警', h3)
        # self.alm_figure(story)
        # add_title(story, '3.3.3 操作告警', h3)
        # self.action_figure(story)
        # add_title(story, '3.3.4 设备告警', h3)
        # self.device_figure(story)

        story.append(PageBreak())
        about_us_3(story)

        doc = MyDocTemplate(path + '/pdf_tmp/audit_report.pdf')
        doc.multiBuild(story, onFirstPage=firstPages, onLaterPages=laterPages)
        # os.rename(path + '/pdf_tmp/overview.pdf', path + '/pdf_tmp/imap_report.pdf')
        """
        add_title(story, '2 专家建议与指导', h1)
        add_title(story, '2.1 总体结论', h2)
        add_title(story, '2.1.1 总体建议', h3)
        self.level_figure(story)
        story.append(Paragraph('总体风险等级为<font color="' + self.grade_color.hexval() + '">' +
                               self.grade + '</font>，建议用户定期进行病毒查杀，及时处理告警防止恶意操作，保证主机'
                                            '的安全。', body))
        add_title(story, '2.1.2 资产清点', h3)
        self.assets_figure(story)
        story.append(Paragraph('当前以上主机存在风险，请用户尽快修复。', body))
        add_title(story, '2.2 安全级别说明', h2)
        security_figure(story)
        add_title(story, '2.3 安全审计依据', h2)
        evidence_table(story)
        story.append(PageBreak())
        """

    # 开始绘制协议事件报告
    def event_go(self):
        story = list()  # 报告内容存储结构
        story.append(PageBreak())
        # 目录
        toc = TableOfContents()
        toc.dotsMinLevel = 0
        toc.levelStyles = [H1, H2, H3]
        story.append(Paragraph('目录', toc1))
        story.append(toc)
        # 分页
        story.append(PageBreak())
        add_title(story, '1 前言', h1)
        add_title(story, '1.1 报告阅读说明', h2)
        story.append(Paragraph('本报告是安全事件情况的统计，主要内容包含主要内容包含攻击源/目标TOP5，安全事件协议分布，安全事件总数随时间分布趋势，'
                               '以及事件来源的分布。', body))
        story.append(Paragraph('北京天地和兴科技有限公司感谢您对我们的信任和支持。现将安全事件报告呈上。', body))
        add_title(story, '1.2 用户选择参数', h2)
        self.base_info_table(story)
        story.append(PageBreak())
        story.append(Paragraph('2 审计概述', h1))
        add_title(story, '2.1 攻击源top5', h2)
        self.src_dst_table(story)
        add_title(story, '2.2 攻击目标top5', h2)
        self.src_dst_table(story)
        add_title(story, '2.3 安全事件协议类型分布图', h2)
        self.proto_figure(story)
        add_title(story, '2.4 安全事件来源分布图', h2)
        self.proto_figure(story)
        add_title(story, '2.5 协议时间分布趋势图', h2)
        self.proto_time(story)

        story.append(PageBreak())
        about_us_3(story)

        doc = MyDocTemplate(path + '/pdf_tmp/event_report.pdf')
        doc.multiBuild(story, onFirstPage=firstPages, onLaterPages=laterPages)

    # 开始绘制协议日志报告
    def log_go(self):
        story = list()  # 报告内容存储结构
        story.append(PageBreak())
        # 目录
        toc = TableOfContents()
        toc.dotsMinLevel = 0
        toc.levelStyles = [H1, H2, H3]
        story.append(Paragraph('目录', toc1))
        story.append(toc)
        # 分页
        story.append(PageBreak())
        add_title(story, '1 前言', h1)
        add_title(story, '1.1 报告阅读说明', h2)
        story.append(Paragraph('本报告是安全事件情况的统计，主要内容包含主要内容包含攻击源/目标TOP5，安全事件协议分布，安全事件总数随时间分布趋势，'
                               '以及事件来源的分布。', body))
        story.append(Paragraph('北京天地和兴科技有限公司感谢您对我们的信任和支持。现将安全事件报告呈上。', body))
        add_title(story, '1.2 用户选择参数', h2)
        self.base_info_table(story)
        story.append(PageBreak())
        story.append(Paragraph('2 审计概述', h1))
        add_title(story, '2.1 攻击源top5', h2)
        self.src_dst_table(story)
        add_title(story, '2.2 攻击目标top5', h2)
        self.src_dst_table(story)
        add_title(story, '2.3 安全事件协议类型分布图', h2)
        self.proto_figure(story)
        add_title(story, '2.4 安全事件来源分布图', h2)
        self.proto_figure(story)
        add_title(story, '2.5 协议时间分布趋势图', h2)
        self.proto_time(story)

        story.append(PageBreak())
        about_us_3(story)

        doc = MyDocTemplate(path + '/pdf_tmp/event_report.pdf')
        doc.multiBuild(story, onFirstPage=firstPages, onLaterPages=laterPages)


if __name__ == "__main__":
    start_time = "2018-10-01"
    end_time = "2018-10-11"
    overview = Overview(start_time, end_time)
    try:
        # 创建临时pdf文件目录
        if not os.path.exists(pdf_tmp):
            os.makedirs(pdf_tmp)
        report_type = input(u"请输入需要生成的报告类型:")
        sys.stderr.write("start make report****************")
        if str(report_type) == "audit":
            overview.proto_go()   # 生成审计报告
            sys.stderr.write("end make report****************")
        elif str(report_type) == "event":
            overview.event_go()   # 生成事件报告
            sys.stderr.write("end make report****************")
        elif str(report_type) == "log":
            overview.log_go()   # 生成日志报告
            sys.stderr.write("end make report****************")
        else:
            sys.stderr.write("input params error.")
        # overview.set_status(1)  # 设置任务状态为完成状态
        # overview.db.close()   # 关闭数据库连接
        print('stop')
    except:
        print('生成失败')
        traceback.print_exc()
        # overview.set_status(2)
