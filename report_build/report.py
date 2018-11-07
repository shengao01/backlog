# -*- coding: utf-8 -*-
__author__ = "zsg"
import traceback
import json
import sys
import os
import time
import logging
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
from logging.handlers import RotatingFileHandler
from logging.handlers import SysLogHandler
from global_function.log_config import GetLogLevelConf


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

logger = logging.getLogger('flask_engine_log')

def _doNothing(canvas, doc):
    '''Dummy callback for onPage'''
    pass

# 第一页模板（封面）
def firstPages(c, doc):
    from app.reportgen import REPORT_TYPE
    # c.drawImage(path + '/Assets/cover_audit.png', 0, 0, width=595.275590551, height=841.88976378)
    if REPORT_TYPE == "audit":
        c.drawImage(path + '/Assets/cover_audit.png', 0, 0, width=595.275590551, height=841.88976378)
    elif REPORT_TYPE == "event":
        c.drawImage(path + '/Assets/cover_event.png', 0, 0, width=595.275590551, height=841.88976378)
    elif REPORT_TYPE == "log":
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
        BaseDocTemplate.build(self, flowables, canvasmaker=canvasmaker)

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


MAP_DICT = {"srcIp": u"源IP", "srcPort": u"源端口", "srcMac": u"源MAC", "destIp": u"目的IP",
              "destPort": u"目的端口", "destMac": u"目的MAC", "protocol": u"协议", "proto": u"协议",
              "start_time": u"开始时间", "end_time": u"结束时间", "srcaddr": u"源地址", "dstaddr": u"目的地址"}

EVENT_SRC_DICT = {"1": "white_list", "2": "black_list", "3": "IPMAC", "4": "traffic_alert"}
# EVENT_EN_CH_DICT = {"white_list": u"白名单", "black_list": u"黑名单", "IPMAC": u"IP/MAC", "traffic_alert": u"流量告警"}
# EVENT_SRC_DICT = {"1": u"白名单", "2": u"黑名单", "3": u"IP/MAC", "4": u"流量告警"}

SYS_LOG_TYPE_DICT = {"1": "device", "2": "interface", "3": "system", "4": "service", "5": "bypass"}
# SYS_LOG_TYPE_DICT = {"1": u"设备", "2": u"接口", "3":  u"系统", "4": u"服务", "5": u"bypass"}

USER_OPER_MAP = {u"用户网页登录": "web_login", u"用户命令行登录": "command_login"}

# SYS_LOG_EN_CH_DICT = {"device": u"设备", "interface": u"接口", "system": u"系统", "service": u"服务", "bypass": u"bypass"}


# 总览报告
class ReportBuild:
    def __init__(self, report_type, report_method, **kwargs):
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
        self.report_method = report_method
        # self.start_time = kwargs["start_time"]  # 开始时间
        # self.end_time = kwargs["end_time"]  # 结束时间
        self.data_dict = kwargs


    def setup_logger(self):
        output_file = '/data/log/flask_engine.log'
        logger = logging.getLogger('flask_engine_log')
        logger.setLevel(GetLogLevelConf())
        # logger.setLevel(logging.INFO)
        # create a rolling file handler
        try:
            handler = RotatingFileHandler(output_file, mode='a',
                                          maxBytes=1024 * 1024 * 10, backupCount=10)
        except:
            handler = SysLogHandler()
        handler.setLevel(GetLogLevelConf())
        # handler.setLevel(logging.INFO)
        handler.setFormatter(
            logging.Formatter("[%(asctime)s -%(levelname)5s- %(filename)20s:%(lineno)3s] %(message)s",
                              "%Y-%m-%d %H:%M:%S"))
        logger.addHandler(handler)

    def base_info_table(self, story):
        # 表格数据
        base_info_data = [['选项', '内容']]
        input_paragram = dict((k, v) for k, v in self.data_dict["input_param"].iteritems() if v.strip())
        # logger.info(self.data_dict["input_param"])
        logger.info(input_paragram)
        for k, v in input_paragram.iteritems():
            base_info_data.append([MAP_DICT[k], v])
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
        # story.append(Paragraph("表 <seq template='1.%(Chart1No+)s'/> 输入参数", table_name))
        story.append(Paragraph("表 <seq template='1.1'/> 输入参数", table_name))
        story.append(base_infor_t)

    # 协议类型分布饼状图
    def proto_figure(self, story):
        json_string = str(self.data_dict["proto_fig_data"]).replace("'", "\"").strip()
        logger.info(json_string)
        # json_string = "{\"modbus\":" + str(self.low) + \
        #               ",\"mms\":" + str(self.medium) + \
        #               ",\"snmp\":" + str(self.low) + "}"
        # json_string = "{\"modbus\": 1, \"snmp\": 1, \"mms\": 1}"
        cmd = phantomjs_path + ' ' + js_path + ' -url ' + \
              path + '/js/charts/tpl/index_event_1.html -width 500 -height 390 -json ' + "'" + \
              json_string + "' -outfile " + path + "/tmp/pro_fig.png"
        # logger.info(cmd)
        os.system(cmd)
        story.append(Image(path + '/tmp/pro_fig.png', width=400, height=312))
        story.append(Paragraph("图 <seq template='2.1'/> 协议类型分布图", figure_name))

    # 源地址-目的地址分布排行
    def src_dst_table(self, story):
        data = [['源地址-目的地址', '审计数目']]
        for flow_data in self.data_dict["proto_order"]:
            data.append([flow_data[0]+"<-->"+flow_data[1], int(flow_data[2])])
        t = Table(data, colWidths=[239, 100], rowHeights=25, spaceAfter=6)
        t.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'hei'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('BACKGROUND', (0, 0), (-1, 0), HexColor(0x31bbf2)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.5, HexColor(0x2a323b)),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(Paragraph("表 <seq template='2.1'/> 源地址-目的地址top5", table_name))
        story.append(t)

    # 协议时间分布趋势图
    def proto_time(self, story):
        # sql = "select virus,year,month,day  from en_servers_option_warn_counter where hour=0 and month!=0 and " \
        #       "day!=0"
        # result = self.db.query(sql, 0)
        xAxis = self.data_dict["proto_time_data"]["time_list"]
        series = self.data_dict["proto_time_data"]["all"]
        # for i in range(len(self.proto_time_data["time"])):
        #     xAxis.append(self.proto_time_data["time"][i])
        #     series.append(self.proto_time_data["all"][i])
        json_dict = {"xAxis": xAxis, "series": series}
        json_string = json.dumps(json_dict)
        cmd = phantomjs_path + ' ' + js_path + ' -url ' + path + '/js/charts/tpl/index_event_3.html  -width 800 ' \
                                               '-height 400 -json ' + "'" + json_string + "' -outfile " + path + \
                                               "/tmp/proto_time.png"
        os.system(cmd)
        story.append(Image(path + '/tmp/proto_time.png', width=439, height=219.5))
        story.append(Paragraph("图 <seq template='2.2'/> 协议时间分布趋势图", figure_name))

    # 传输层协议分布饼状图
    # def l2_figure(self, story):
    #     json_string = "{\"TCP\":" + str(self.low) + \
    #                   ",\"UDP\":" + str(self.medium) + \
    #                   ",\"GOOSE\":" + str(self.high) + "}"
    #     cmd = phantomjs_path + ' ' + js_path + ' -url ' + \
    #           path + '/js/charts/tpl/index_proto_3.html -width 500 -height 390 -json ' + "'" + \
    #           json_string + "' -outfile " + path + "/tmp/l2.png"
    #     # cmd = phantomjs_path + ' ' + js_path + ' -url ' + \
    #     #       path + '/js/charts/tpl/index_text_1.html -width 500 -height 390 ' + " -outfile " + path + "/tmp/1.png"
    #     os.system(cmd)
    #     story.append(Image(path + '/tmp/l2.png', width=400, height=312))
    #     story.append(Paragraph("图 <seq template='2.3'/> 协议类型分布图", figure_name))

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
        story.append(Paragraph('本报告是协议审计情况的统计，主要内容包含协议类型分布，TOP特征值展示，'
                               '以及协议数随时间分布趋势。', body))
        story.append(Paragraph('北京天地和兴科技有限公司感谢您对我们的信任和支持。现将安全审计报告呈上。', body))
        if self.report_method in [1, 2, 3]:
            add_title(story, '1.2 周期性报表', h2)
        else:
            add_title(story, '1.2 自定义报表', h2)
        self.base_info_table(story)
        story.append(PageBreak())
        story.append(Paragraph('2 审计概述', h1))
        add_title(story, '2.1 协议类型分布图', h2)
        self.proto_figure(story)
        add_title(story, '2.2 源地址-目的地址top5', h2)
        self.src_dst_table(story)
        story.append(PageBreak())
        add_title(story, '2.3 协议时间分布趋势图', h2)
        self.proto_time(story)
        # add_title(story, '2.4 传输层分布', h2)
        # self.l2_figure(story)
        # story.append(PageBreak())
        # about_us_3(story)

        try:
            doc = MyDocTemplate(path + '/pdf_tmp/audit_report.pdf')
            logger.info("====================enter multiBuild.............")
            doc.multiBuild(story, onFirstPage=firstPages, onLaterPages=laterPages)
            os.system("rm -rf " + path + "/tmp/")
            os.system("mv " + path + "/pdf_tmp/audit_report.pdf " + "/data/report/protocal/")
        except:
            logger.error("MyDocTemplate build error.")
            logger.error(traceback.format_exc())

    # 攻击源分布排行表
    def src_table(self, story):
        data = [['源地址', '事件条数']]
        for row in self.data_dict["srcaddr_order"]:
            data.append([row[0], int(row[1])])

        t = Table(data, colWidths=[239, 100, 100], rowHeights=25, spaceAfter=6)
        t.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'hei'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('BACKGROUND', (0, 0), (-1, 0), HexColor(0x31bbf2)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.5, HexColor(0x2a323b)),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(Paragraph("表 <seq template='2.1'/> 源地址top5", table_name))
        story.append(t)

    # 攻击目标分布排行表
    def dst_table(self, story):
        data = [['目的地址', '事件条数']]
        for row in self.data_dict["dstaddr_order"]:
            data.append([row[0], int(row[1])])

        t = Table(data, colWidths=[239, 100, 100], rowHeights=25, spaceAfter=6)
        t.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'hei'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('BACKGROUND', (0, 0), (-1, 0), HexColor(0x31bbf2)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.5, HexColor(0x2a323b)),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(Paragraph("表 <seq template='2.2'/> 目的地址top5", table_name))
        story.append(t)

    # 安全事件协议类型分布图
    def event_proto_figure(self, story):
        # json_string = "{\"snmp\":" + str(self.low) + \
        #               ",\"dnp3\":" + str(self.medium) + \
        #               ",\"other\":" + str(self.high) + "}"
        json_dict = {}
        logger.info(self.data_dict["event_proto_fig"])
        for row in self.data_dict["event_proto_fig"]:
            json_dict[row[0]] = int(row[1])
        logger.info(json_dict)
        json_string = str(json_dict).replace("'", "\"").strip()
        logger.info(json_string)
        cmd = phantomjs_path + ' ' + js_path + ' -url ' + \
              path + '/js/charts/tpl/index_event_1.html -width 500 -height 390 -json ' + "'" + \
              json_string + "' -outfile " + path + "/tmp/event_fig.png"
        logger.info(cmd)
        os.system(cmd)
        story.append(Image(path + '/tmp/event_fig.png', width=400, height=312))
        story.append(Paragraph("图 <seq template='2.1'/> 安全事件协议类型分布图", figure_name))

    # 安全事件来源分布图
    def event_src_figure(self, story):
        # json_string = "{\"IPMAC\":" + str(self.low) + \
        #               ",\"white_list\":" + str(self.medium) + \
        #               ",\"traffic_alert\":" + str(self.medium) + \
        #               ",\"black_list\":" + str(self.high) + "}"
        json_dict = {}
        logger.info(self.data_dict["event_src"])
        for row in self.data_dict["event_src"]:
            json_dict[EVENT_SRC_DICT[str(row[0])]] = int(row[1])
        logger.info(json_dict)
        json_string = str(json_dict).replace("'", "\"").strip()
        logger.info(json_string)
        cmd = phantomjs_path + ' ' + js_path + ' -url ' + \
              path + '/js/charts/tpl/index_event_1.html -width 500 -height 390 -json ' + "'" + \
              json_string + "' -outfile " + path + "/tmp/event_src_fig.png"
        logger.info(cmd)
        os.system(cmd)
        story.append(Image(path + '/tmp/event_src_fig.png', width=400, height=312))
        story.append(Paragraph("图 <seq template='2.2'/> 安全事件来源分布图", figure_name))

    # 安全事件趋势分布图
    def event_time(self, story):
        xAxis = list()
        series = list()
        logger.info(self.data_dict["event_time_data"])
        for row in self.data_dict["event_time_data"]:
            xAxis.append(row[0])
            series.append(int(row[1]) + int(row[2]))
        # for i in range(len(self.proto_time_data["time"])):
        #     xAxis.append(self.proto_time_data["time"][i])
        #     series.append(self.proto_time_data["all"][i])
        json_dict = {"xAxis": xAxis, "series": series}
        json_string = json.dumps(json_dict)
        cmd = phantomjs_path + ' ' + js_path + ' -url ' + path + '/js/charts/tpl/index_event_3.html  -width 800 ' \
                                               '-height 400 -json ' + "'" + json_string + "' -outfile " + path + \
                                               "/tmp/event_time.png"
        logger.info("event_time: " + cmd)
        os.system(cmd)
        story.append(Image(path + '/tmp/event_time.png', width=439, height=219.5))
        story.append(Paragraph("图 <seq template='2.3'/> 安全事件分布趋势图", figure_name))

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
        story.append(Paragraph('本报告是安全事件情况的统计，主要内容包含主要内容包含攻击源/目标TOP5，安全事件协议分布，安全事件来源分布，'
                               '以及安全事件总数随时间分布趋势。', body))
        story.append(Paragraph('北京天地和兴科技有限公司感谢您对我们的信任和支持。现将安全事件报告呈上。', body))
        if self.report_method in [1, 2, 3]:
            add_title(story, '1.2 周期性报表', h2)
        else:
            add_title(story, '1.2 自定义报表', h2)
        self.base_info_table(story)
        story.append(PageBreak())
        story.append(Paragraph('2 安全事件概述', h1))
        add_title(story, '2.1 源地址top5', h2)
        self.src_table(story)
        add_title(story, '2.2 目的地址top5', h2)
        self.dst_table(story)
        story.append(PageBreak())
        add_title(story, '2.3 安全事件协议类型分布图', h2)
        self.event_proto_figure(story)
        story.append(PageBreak())
        add_title(story, '2.4 安全事件来源分布图', h2)
        self.event_src_figure(story)
        add_title(story, '2.5 事件时间分布趋势图', h2)
        self.event_time(story)

        story.append(PageBreak())
        # about_us_3(story)

        try:
            doc = MyDocTemplate(path + '/pdf_tmp/event_report.pdf')
            logger.info("====================enter multiBuild.............")
            doc.multiBuild(story, onFirstPage=firstPages, onLaterPages=laterPages)
            os.system("rm -rf " + path + "/tmp/")
            os.system("mv " + path + "/pdf_tmp/event_report.pdf " + "/data/report/alarm/")
        except:
            logger.error("MyDocTemplate build error.")
            logger.error(traceback.format_exc())

    # 用户登录ip排行
    def login_figure(self, story):
        data = [['ip地址', '日志条数']]
        for row in self.data_dict["user_ip_table"]:
            data.append([row[0], int(row[1])])
        t = Table(data, colWidths=[239, 100, 100], rowHeights=25, spaceAfter=6)
        t.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'hei'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('BACKGROUND', (0, 0), (-1, 0), HexColor(0x31bbf2)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.5, HexColor(0x2a323b)),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(Paragraph("表 <seq template='2.1.1'/> 操作用户ip地址top5", table_name))
        story.append(t)

    # 用户操作分布图
    def oper_figure(self, story):
        # json_string = "{\"web\":" + str(self.low) + \
        #               ",\"command\":" + str(self.medium) + \
        #               ",\"other\":" + str(self.high) + "}"
        json_dict = {"common": 0}
        data_list = self.data_dict["oper_fig"]
        for row in data_list:
            if row[0] == "用户命令行登录":
                json_dict["command_login"] = int(row[1])
            elif row[0] == "用户网页登录":
                json_dict["web_login"] = int(row[1])
            else:
                json_dict["common"] += row[1]
        json_string = json.dumps(json_dict)
        cmd = phantomjs_path + ' ' + js_path + ' -url ' + \
              path + '/js/charts/tpl/index_event_1.html -width 500 -height 390 -json ' + "'" + \
              json_string + "' -outfile " + path + "/tmp/oper_fig.png"
        logger.info(cmd)
        os.system(cmd)
        story.append(Image(path + '/tmp/oper_fig.png', width=400, height=312))
        story.append(Paragraph("图 <seq template='2.1.1'/> 用户操作分布图", figure_name))

    # 用户操作日志趋势分布图
    def oper_log_time(self, story):
        xAxis = list()
        series = list()
        data_list = self.data_dict["oper_log_time"]
        for row in data_list:
            xAxis.append(row[0])
            series.append(int(row[1]))
        # for i in range(len(self.proto_time_data["time"])):
        #     xAxis.append(self.proto_time_data["time"][i])
        #     series.append(self.proto_time_data["all"][i])
        json_dict = {"xAxis": xAxis, "series": series}
        logger.info(json_dict)
        json_string = json.dumps(json_dict)
        cmd = phantomjs_path + ' ' + js_path + ' -url ' + path + '/js/charts/tpl/index_event_3.html  -width 800 ' \
                                               '-height 400 -json ' + "'" + json_string + "' -outfile " + path + \
                                               "/tmp/oper_log_time.png"
        os.system(cmd)
        story.append(Image(path + '/tmp/oper_log_time.png', width=439, height=219.5))
        story.append(Paragraph("图 <seq template='2.1.3'/> 用户操作日志时间分布趋势图", figure_name))

    # 系统日志分布
    def sys_figure(self, story):
        # json_string = "{\"yewu\":" + str(self.low) + \
        #               ",\"eth\":" + str(self.medium) + \
        #               ",\"sys\":" + str(self.high) + "}"
        json_dict = {}
        data_list = self.data_dict["sys_log_fig"]
        for row in data_list:
            json_dict[SYS_LOG_TYPE_DICT[str(row[0])]] = int(row[1])
        logger.info(json_dict)
        json_string = str(json_dict).replace("'", "\"").strip()
        logger.info(json_string)
        cmd = phantomjs_path + ' ' + js_path + ' -url ' + \
              path + '/js/charts/tpl/index_event_1.html -width 500 -height 390 -json ' + "'" + \
              json_string + "' -outfile " + path + "/tmp/sys_fig.png"
        os.system(cmd)
        story.append(Image(path + '/tmp/sys_fig.png', width=400, height=312))
        story.append(Paragraph("图 <seq template='2.2.1'/> 系统日志分布", figure_name))

    # 系统警告日志趋势分布图
    def alarm_log_time(self, story):
        xAxis = list()
        series = list()
        data_list = self.data_dict["alarm_log_time"]
        for row in data_list:
            xAxis.append(row[0])
            series.append(int(row[1]))
        # for i in range(len(self.proto_time_data["time"])):
        #     xAxis.append(self.proto_time_data["time"][i])
        #     series.append(self.proto_time_data["all"][i])
        json_dict = {"xAxis": xAxis, "series": series}
        logger.info(json_dict)
        json_string = json.dumps(json_dict)
        cmd = phantomjs_path + ' ' + js_path + ' -url ' + path + '/js/charts/tpl/index_event_3.html  -width 800 ' \
                                               '-height 400 -json ' + "'" + json_string + "' -outfile " + path + \
                                               "/tmp/alarm_log_time.png"
        os.system(cmd)
        story.append(Image(path + '/tmp/alarm_log_time.png', width=439, height=219.5))
        story.append(Paragraph("图 <seq template='2.2.2'/> 系统警告日志分布趋势图", figure_name))

    # 系统日志趋势分布图
    def sys_log_time(self, story):
        xAxis = list()
        series = list()
        data_list = self.data_dict["sys_log_time"]
        for row in data_list:
            xAxis.append(row[0])
            series.append(int(row[1]))
        # for i in range(len(self.proto_time_data["time"])):
        #     xAxis.append(self.proto_time_data["time"][i])
        #     series.append(self.proto_time_data["all"][i])
        json_dict = {"xAxis": xAxis, "series": series}
        logger.info(json_dict)
        json_string = json.dumps(json_dict)
        cmd = phantomjs_path + ' ' + js_path + ' -url ' + path + '/js/charts/tpl/index_event_3.html  -width 800 ' \
                                               '-height 400 -json ' + "'" + json_string + "' -outfile " + path + \
                                               "/tmp/sys_log_time.png"
        os.system(cmd)
        story.append(Image(path + '/tmp/sys_log_time.png', width=439, height=219.5))
        story.append(Paragraph("图 <seq template='2.2.3'/> 系统日志分布趋势图", figure_name))

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
        story.append(Paragraph('本报告是对操作日志及系统日志的统计。操作日志主要内容包括操作用户ip地址top5，用户操作情况统计，'
                               '以及用户操作日志随时间分布趋势。', body))
        story.append(Paragraph('系统日志主要内容包括系统日志分布情况，系统警告日志数量趋势分布，'
                               '以及系统日志总数随时间分布趋势。', body))
        story.append(Paragraph('北京天地和兴科技有限公司感谢您对我们的信任和支持。现将安全事件报告呈上。', body))
        if self.report_method in [1, 2, 3]:
            add_title(story, '1.2 周期性报表', h2)
        else:
            add_title(story, '1.2 自定义报表', h2)
        self.base_info_table(story)
        story.append(PageBreak())
        story.append(Paragraph('2 日志概述', h1))
        add_title(story, '2.1 操作日志概述', h2)
        add_title(story, '2.1.1 操作用户ip地址top5', h3)
        self.login_figure(story)
        add_title(story, '2.1.2 用户操作分布情况', h3)
        self.oper_figure(story)
        story.append(PageBreak())
        add_title(story, '2.1.3 用户操作日志趋势分布', h3)
        self.oper_log_time(story)
        story.append(PageBreak())
        add_title(story, '2.2 系统日志概述', h2)
        add_title(story, '2.2.1 系统日志分布情况', h3)
        self.sys_figure(story)
        add_title(story, '2.2.2 系统警告日志趋势分布', h3)
        self.alarm_log_time(story)
        story.append(PageBreak())
        add_title(story, '2.2.3 系统日志趋势分布', h3)
        self.sys_log_time(story)

        story.append(PageBreak())
        # about_us_3(story)

        doc = MyDocTemplate(path + '/pdf_tmp/log_report.pdf')
        doc.multiBuild(story, onFirstPage=firstPages, onLaterPages=laterPages)
        os.system("rm -rf " + path + "/tmp/")
        os.system("mv " + path + "/pdf_tmp/log_report.pdf " + "/data/report/log/")

    # 根据用户输入, 启动对应的执行代码,生成报告
    def run(self):
        try:
            self.setup_logger()
            # 创建临时pdf文件目录
            if not os.path.exists(pdf_tmp):
                os.makedirs(pdf_tmp)
            if self.report_type == "audit":
                logger.info('enter generate audit report=================')
                self.proto_go()  # 生成审计报告
            elif self.report_type == "event":
                logger.info('enter generate event report=================')
                self.event_go()  # 生成事件报告
            elif self.report_type == "log":
                logger.info('enter generate log report=================')
                self.log_go()  # 生成日志报告
            else:
                logger.info("input params error.")
        except:
            logger.info('generate error')
            logger.info(traceback.format_exc())


if __name__ == "__main__":
    info_dict = {"start_time": "2018-10-01", "end_time": "2018-10-11"}
    report_type = "audit"
    Overview = ReportBuild(report_type, **info_dict)
    Overview.run()
