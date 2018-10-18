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


def _doNothing(canvas, doc):
    '''Dummy callback for onPage'''
    pass


# 第一页模板（封面）
def firstPages(c, doc):
    if overview.report_type == "audit":
        c.drawImage(path + '/Assets/cover_audit.png', 0, 0, width=595.275590551, height=841.88976378)
    elif overview.report_type == "event":
        c.drawImage(path + '/Assets/cover_event.png', 0, 0, width=595.275590551, height=841.88976378)
    elif overview.report_type == "log":
        c.drawImage(path + '/Assets/cover_log.png', 0, 0, width=595.275590551, height=841.88976378)
    else:
        pass


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
    def __init__(self, start_time, end_time, report_type, proto_type=None):
        # self.db = Db()  # 连接数据库
        self.grade_color = HexColor(0xe20c1e)   # 等级颜色
        self.id = None  # 报告id
        self.name = None  # 任务名称
        self.high = 5   # 病毒木马数量
        self.medium = 6  # 程序告警数量 + 设备告警数量
        self.low = 7    # 操作告警数量
        self.alm = 0    # 程序告警数量
        self.dev = 0    # 设备告警数量
        self.total = 0  # 总数
        self.report_type = report_type
        self.start_time = start_time  # 开始时间
        self.end_time = end_time  # 结束时间
        self.src_dst = [["192.168.81.135<--->192.168.81.24", "SNMP", "3", "10%"],
                        ["192.168.81.135<--->192.168.81.24", "SNMP", "3", "10%"],
                        ["192.168.81.135<--->192.168.81.24", "SNMP", "3", "10%"],
                        ["192.168.81.135<--->192.168.81.24", "SNMP", "3", "10%"],
                        ["192.168.81.135<--->192.168.81.24", "SNMP", "3", "10%"]]
        self.proto_time_data = {"time": ['00:00', '01:00', '02:00', '03:00', '04:00', '05:00', '06:00', '07:00', '08:00', '09:00', '10:00', '11:00', '12:00', '13:00', '14:00', '15:00', '16:00', '17:00', '18:00', '19:00', '20:00', '21:00', '22:00', '23:00'],
                                "all": [26, 20, 26, 26, 26, 16, 26, 26, 30, 26, 26, 26, 20, 34, 26, 26, 26, 23, 26, 39, 26, 18, 26, 22]}

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
              json_string + "' -outfile " + path + "/tmp/pro_fig.png"
        os.system(cmd)
        story.append(Image(path + '/tmp/pro_fig.png', width=400, height=312))
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
              json_string + "' -outfile " + path + "/tmp/l2.png"
        # cmd = phantomjs_path + ' ' + js_path + ' -url ' + \
        #       path + '/js/charts/tpl/index_text_1.html -width 500 -height 390 ' + " -outfile " + path + "/tmp/1.png"
        os.system(cmd)
        story.append(Image(path + '/tmp/l2.png', width=400, height=312))
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
        add_title(story, '1.2 自定义报表', h2)
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
        self.risk_stats_table(story)
        self.risk_type_figure(story)
        add_title(story, '3.2.3 风险类型分布', h3)
        self.type_figure(story)
        self.type_stats_table(story)
        add_title(story, '3.3.1 病毒木马', h3)
        self.virus_figure(story)
        add_title(story, '3.3.2 程序告警', h3)
        self.alm_figure(story)
        add_title(story, '3.3.3 操作告警', h3)
        self.action_figure(story)
        add_title(story, '3.3.4 设备告警', h3)
        self.device_figure(story)
        """

    # 攻击源分布排行表
    def src_table(self, story):
        data = [['源地址', '比例'],
                [self.src_dst[0][0], self.src_dst[0][3]],
                [self.src_dst[0][0], self.src_dst[0][3]],
                [self.src_dst[0][0], self.src_dst[0][3]],
                [self.src_dst[0][0], self.src_dst[0][3]],
                [self.src_dst[0][0], self.src_dst[0][3]]
                ]

        t = Table(data, colWidths=[339, 100], rowHeights=25, spaceAfter=6)
        t.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'hei'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('BACKGROUND', (0, 0), (-1, 0), HexColor(0x31bbf2)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.5, HexColor(0x2a323b)),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(Paragraph("表 <seq template='2.%(Chart3No+)s'/> 攻击源地址分布排行", table_name))
        story.append(t)

    # 攻击目标分布排行表
    def dst_table(self, story):
        data = [['目的地址', '比例'],
                [self.src_dst[0][0], self.src_dst[0][3]],
                [self.src_dst[0][0], self.src_dst[0][3]],
                [self.src_dst[0][0], self.src_dst[0][3]],
                [self.src_dst[0][0], self.src_dst[0][3]],
                [self.src_dst[0][0], self.src_dst[0][3]]
                ]

        t = Table(data, colWidths=[339, 100], rowHeights=25, spaceAfter=6)
        t.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'hei'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('BACKGROUND', (0, 0), (-1, 0), HexColor(0x31bbf2)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.5, HexColor(0x2a323b)),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(Paragraph("表 <seq template='2.%(Chart3No+)s'/> 目的地址分布排行", table_name))
        story.append(t)

    # 安全事件协议类型分布图
    def event_proto_figure(self, story):
        json_string = "{\"snmp\":" + str(self.low) + \
                      ",\"dnp3\":" + str(self.medium) + \
                      ",\"other\":" + str(self.high) + "}"
        cmd = phantomjs_path + ' ' + js_path + ' -url ' + \
              path + '/js/charts/tpl/index_event_1.html -width 500 -height 390 -json ' + "'" + \
              json_string + "' -outfile " + path + "/tmp/event_fig.png"
        os.system(cmd)
        story.append(Image(path + '/tmp/event_fig.png', width=400, height=312))
        story.append(Paragraph("图 <seq template='2.%(Figure3No+)s'/> 安全事件协议类型分布图", figure_name))

    # 安全事件来源分布图
    def event_src_figure(self, story):
        json_string = "{\"IPMAC\":" + str(self.low) + \
                      ",\"white_list\":" + str(self.medium) + \
                      ",\"traffic_alert\":" + str(self.medium) + \
                      ",\"black_list\":" + str(self.high) + "}"
        cmd = phantomjs_path + ' ' + js_path + ' -url ' + \
              path + '/js/charts/tpl/index_event_2.html -width 500 -height 390 -json ' + "'" + \
              json_string + "' -outfile " + path + "/tmp/event_src_fig.png"
        os.system(cmd)
        story.append(Image(path + '/tmp/event_src_fig.png', width=400, height=312))
        story.append(Paragraph("图 <seq template='2.%(Figure3No+)s'/> 安全事件来源分布图", figure_name))

    # 安全事件趋势分布图
    def event_time(self, story):
        xAxis = list()
        series = list()
        for i in range(len(self.proto_time_data["time"])):
            xAxis.append(self.proto_time_data["time"][i])
            series.append(self.proto_time_data["all"][i])
        json_dict = {"xAxis": xAxis, "series": series}
        json_string = json.dumps(json_dict)
        cmd = phantomjs_path + ' ' + js_path + ' -url ' + path + '/js/charts/tpl/index_event_3.html  -width 800 ' \
                                               '-height 400 -json ' + "'" + json_string + "' -outfile " + path + \
                                               "/tmp/event_time.png"
        os.system(cmd)
        story.append(Image(path + '/tmp/event_time.png', width=439, height=219.5))
        story.append(Paragraph("图 <seq template='2.%(Figure3No+)s'/> 安全事件分布趋势图", figure_name))

    # 开始绘制安全事件报告
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
        self.src_table(story)
        add_title(story, '2.2 攻击目标top5', h2)
        self.dst_table(story)
        add_title(story, '2.3 安全事件协议类型分布图', h2)
        self.event_proto_figure(story)
        add_title(story, '2.4 安全事件来源分布图', h2)
        self.event_src_figure(story)
        add_title(story, '2.5 事件时间分布趋势图', h2)
        self.event_time(story)

        story.append(PageBreak())
        about_us_3(story)

        doc = MyDocTemplate(path + '/pdf_tmp/event_report.pdf')
        doc.multiBuild(story, onFirstPage=firstPages, onLaterPages=laterPages)

    # 用户登录分布图
    def login_figure(self, story):
        json_string = "{\"test\":" + str(self.low) + \
                      ",\"admin\":" + str(self.medium) + \
                      ",\"other\":" + str(self.high) + "}"
        cmd = phantomjs_path + ' ' + js_path + ' -url ' + \
              path + '/js/charts/tpl/index_log_1.html -width 500 -height 390 -json ' + "'" + \
              json_string + "' -outfile " + path + "/tmp/login_fig.png"
        os.system(cmd)
        story.append(Image(path + '/tmp/login_fig.png', width=400, height=312))
        story.append(Paragraph("图 <seq template='2.%(Figure3No+)s'/> 用户登录分布图", figure_name))

    # 用户操作分布图
    def oper_figure(self, story):
        json_string = "{\"web\":" + str(self.low) + \
                      ",\"command\":" + str(self.medium) + \
                      ",\"other\":" + str(self.high) + "}"
        cmd = phantomjs_path + ' ' + js_path + ' -url ' + \
              path + '/js/charts/tpl/index_log_2.html -width 500 -height 390 -json ' + "'" + \
              json_string + "' -outfile " + path + "/tmp/oper_fig.png"
        os.system(cmd)
        story.append(Image(path + '/tmp/oper_fig.png', width=400, height=312))
        story.append(Paragraph("图 <seq template='2.%(Figure3No+)s'/> 用户操作分布图", figure_name))

    # 用户操作日志趋势分布图
    def oper_log_time(self, story):
        xAxis = list()
        series = list()
        for i in range(len(self.proto_time_data["time"])):
            xAxis.append(self.proto_time_data["time"][i])
            series.append(self.proto_time_data["all"][i])
        json_dict = {"xAxis": xAxis, "series": series}
        json_string = json.dumps(json_dict)
        cmd = phantomjs_path + ' ' + js_path + ' -url ' + path + '/js/charts/tpl/index_log_3.html  -width 800 ' \
                                               '-height 400 -json ' + "'" + json_string + "' -outfile " + path + \
                                               "/tmp/oper_log_time.png"
        os.system(cmd)
        story.append(Image(path + '/tmp/oper_log_time.png', width=439, height=219.5))
        story.append(Paragraph("图 <seq template='2.%(Figure3No+)s'/> 用户操作日志时间分布趋势图", figure_name))

    # 系统日志分布
    def sys_figure(self, story):
        json_string = "{\"yewu\":" + str(self.low) + \
                      ",\"eth\":" + str(self.medium) + \
                      ",\"sys\":" + str(self.high) + "}"
        cmd = phantomjs_path + ' ' + js_path + ' -url ' + \
              path + '/js/charts/tpl/index_log_4.html -width 500 -height 390 -json ' + "'" + \
              json_string + "' -outfile " + path + "/tmp/sys_fig.png"
        os.system(cmd)
        story.append(Image(path + '/tmp/sys_fig.png', width=400, height=312))
        story.append(Paragraph("图 <seq template='2.%(Figure3No+)s'/> 系统日志分布", figure_name))

    # 系统警告日志趋势分布图
    def alarm_log_time(self, story):
        xAxis = list()
        series = list()
        for i in range(len(self.proto_time_data["time"])):
            xAxis.append(self.proto_time_data["time"][i])
            series.append(self.proto_time_data["all"][i])
        json_dict = {"xAxis": xAxis, "series": series}
        json_string = json.dumps(json_dict)
        cmd = phantomjs_path + ' ' + js_path + ' -url ' + path + '/js/charts/tpl/index_log_5.html  -width 800 ' \
                                               '-height 400 -json ' + "'" + json_string + "' -outfile " + path + \
                                               "/tmp/alarm_log_time.png"
        os.system(cmd)
        story.append(Image(path + '/tmp/alarm_log_time.png', width=439, height=219.5))
        story.append(Paragraph("图 <seq template='2.%(Figure3No+)s'/> 系统警告日志分布趋势图", figure_name))

    # 系统日志趋势分布图
    def sys_log_time(self, story):
        xAxis = list()
        series = list()
        for i in range(len(self.proto_time_data["time"])):
            xAxis.append(self.proto_time_data["time"][i])
            series.append(self.proto_time_data["all"][i])
        json_dict = {"xAxis": xAxis, "series": series}
        json_string = json.dumps(json_dict)
        cmd = phantomjs_path + ' ' + js_path + ' -url ' + path + '/js/charts/tpl/index_log_6.html  -width 800 ' \
                                               '-height 400 -json ' + "'" + json_string + "' -outfile " + path + \
                                               "/tmp/sys_log_time.png"
        os.system(cmd)
        story.append(Image(path + '/tmp/sys_log_time.png', width=439, height=219.5))
        story.append(Paragraph("图 <seq template='2.%(Figure3No+)s'/> 系统日志分布趋势图", figure_name))

    # 开始绘制日志报告
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
        story.append(Paragraph('2 日志概述', h1))
        add_title(story, '2.1 操作日志概述', h2)
        add_title(story, '2.1.1 用户登录分布情况', h3)
        self.login_figure(story)
        add_title(story, '2.1.2 用户操作分布情况', h3)
        self.oper_figure(story)
        add_title(story, '2.1.3 用户操作日志趋势分布', h3)
        self.oper_log_time(story)
        add_title(story, '2.2 系统日志概述', h2)
        add_title(story, '2.2.1 系统日志分布情况', h3)
        self.sys_figure(story)
        add_title(story, '2.2.2 系统警告日志趋势分布', h3)
        self.alarm_log_time(story)
        add_title(story, '2.2.3 系统日志趋势分布', h3)
        self.sys_log_time(story)

        story.append(PageBreak())
        about_us_3(story)

        doc = MyDocTemplate(path + '/pdf_tmp/log_report.pdf')
        doc.multiBuild(story, onFirstPage=firstPages, onLaterPages=laterPages)

    # 根据用户输入, 启动对应的执行代码,生成报告
    def run(self):
        try:
            # 创建临时pdf文件目录
            if not os.path.exists(pdf_tmp):
                os.makedirs(pdf_tmp)
            print(str(path))
            sys.stderr.write("start make report****************")
            if self.report_type == "audit":
                self.proto_go()  # 生成审计报告
                sys.stderr.write("end make report****************")
            elif self.report_type == "event":
                self.event_go()  # 生成事件报告
                sys.stderr.write("end make report****************")
            elif self.report_type == "log":
                self.log_go()  # 生成日志报告
                sys.stderr.write("end make report****************")
            else:
                sys.stderr.write("input params error.")
            # overview.set_status(1)  # 设置任务状态为完成状态
            # overview.db.close()   # 关闭数据库连接
            print('stop')
        except:
            print('生成失败')
            print(traceback.format_exc())


if __name__ == "__main__":
    start_time = "2018-10-01"
    end_time = "2018-10-11"
    report_type = str(input(u"请输入需要生成的报告类型:"))
    overview = Overview(start_time, end_time, report_type)
    overview.run()
