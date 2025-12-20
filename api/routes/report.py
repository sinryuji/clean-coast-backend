from fastapi import APIRouter, HTTPException, Depends, Response
from sqlalchemy.orm import Session
from core.database import get_db
from core.auth import get_current_user
from datetime import date
from io import BytesIO
from pydantic import BaseModel
from typing import Optional
import os
from urllib.parse import quote

# ReportLab imports
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.graphics.shapes import Drawing, Line
from reportlab.graphics.charts.linecharts import HorizontalLineChart
from reportlab.graphics.charts.axes import XCategoryAxis

# dashboard 로직 재사용
from api.routes.dashboard import (
    get_dashboard,
    RiskLevel,
    ActionType
)

router = APIRouter(
    prefix="/v1/report",
    tags=["report"]
)


class ReportRequest(BaseModel):
    organization_name: str = "해양환경공단"


def register_korean_font():
    """한글 폰트 등록 (NotoSansKR 폰트 사용)"""
    try:
        # 프로젝트 내 폰트 경로
        font_path = os.path.join(os.path.dirname(__file__), '..', '..', 'fonts', 'NotoSansKR-Regular.ttf')
        font_path = os.path.abspath(font_path)
        
        # Bold 폰트 경로
        bold_font_path = os.path.join(os.path.dirname(__file__), '..', '..', 'fonts', 'NotoSansKR-Bold.ttf')
        bold_font_path = os.path.abspath(bold_font_path)
        
        if os.path.exists(font_path):
            pdfmetrics.registerFont(TTFont('Korean', font_path))
            # Bold 폰트도 등록 (있는 경우)
            if os.path.exists(bold_font_path):
                pdfmetrics.registerFont(TTFont('Korean-Bold', bold_font_path))
            return 'Korean'
        else:
            raise FileNotFoundError(f"폰트 파일을 찾을 수 없습니다: {font_path}")
    except Exception as e:
        # 폰트 등록 실패 시 기본 폰트 사용
        print(f"폰트 등록 실패: {e}")
        return 'Helvetica'


def create_pdf_report(dashboard_data, buffer, organization_name="해양환경공단", logo_path=None):
    """PDF 보고서 생성
    
    Args:
        dashboard_data: DashboardResponse 데이터
        buffer: BytesIO 버퍼
        organization_name: 발행 기관명
        logo_path: 로고 이미지 경로
    """
    # 한글 폰트 등록
    korean_font = register_korean_font()
    
    # PDF 문서 생성
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20*mm,
        leftMargin=20*mm,
        topMargin=10*mm,
        bottomMargin=20*mm
    )
    
    # 스타일 정의
    styles = getSampleStyleSheet()
    
    # 제목 스타일
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontName=korean_font,
        fontSize=20,
        textColor=colors.HexColor('#1a1a1a'),
        alignment=TA_CENTER,
        spaceAfter=2*mm
    )
    
    # 부제목 스타일
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontName=korean_font,
        fontSize=14,
        textColor=colors.HexColor('#666666'),
        alignment=TA_CENTER,
        spaceAfter=3*mm
    )
    
    # 섹션 제목 스타일
    section_title_style = ParagraphStyle(
        'SectionTitle',
        parent=styles['Heading2'],
        fontName='Korean-Bold' if 'Korean-Bold' in pdfmetrics.getRegisteredFontNames() else korean_font,
        fontSize=14,
        textColor=colors.HexColor('#1a1a1a'),
        spaceAfter=2*mm,
        spaceBefore=4*mm
    )
    
    # 본문 스타일
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['Normal'],
        fontName=korean_font,
        fontSize=10,
        textColor=colors.HexColor('#333333'),
        leading=14
    )
    
    # 문서 요소 리스트
    elements = []
    
    # 헤더 섹션 (로고 + 기관명 + 발행연도)
    year, month = dashboard_data.target_month.split('-')
    current_year = date.today().year
    
    # 로고 이미지 추가 (우측 상단)
    if logo_path and os.path.exists(logo_path):
        try:
            logo = Image(logo_path, width=15*mm, height=15*mm)
            org_text = Paragraph(
                f'<font name="{korean_font}" size="15">{organization_name}</font>',
                ParagraphStyle('OrgStyle', alignment=TA_LEFT, fontName=korean_font)
            )
            year_text = Paragraph(
                f'<font name="{korean_font}" size="9" color="black">발행 연도: {current_year}-{month}-REPORT</font>',
                ParagraphStyle('YearStyle', alignment=TA_RIGHT, fontName=korean_font, textColor=colors.grey, wordWrap='LTR')
            )
            
            # 우측 정렬을 위한 테이블 (로고와 기관명을 가로로 배치)
            header_data = [
                ['', logo, org_text],
                ['', '', year_text]
            ]
            
            header_table = Table(header_data, colWidths=[120*mm, 17*mm, 43*mm])
            header_table.setStyle(TableStyle([
                ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
                ('ALIGN', (2, 0), (2, 0), 'LEFT'),
                ('ALIGN', (2, 1), (2, 1), 'RIGHT'),
                ('VALIGN', (1, 0), (2, 0), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('LEFTPADDING', (2, 0), (2, 0), 3*mm),
                ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                ('TOPPADDING', (0, 0), (-1, -1), 0),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ]))
            elements.append(header_table)
            elements.append(Spacer(1, 1*mm))
        except Exception as e:
            print(f"로고 이미지 로드 실패: {e}")
    else:
        # 로고 없이 텍스트만
        org_style = ParagraphStyle(
            'OrgHeader',
            parent=styles['Normal'],
            fontName=korean_font,
            fontSize=9,
            alignment=TA_RIGHT,
            textColor=colors.grey
        )
        elements.append(Paragraph(f"{organization_name}", org_style))
        elements.append(Paragraph(f"발행 연도: {current_year}-{month}-REPORT", org_style))
        elements.append(Spacer(1, 1*mm))
    
    # 1. 제목
    title = Paragraph(f"제주 해양쓰레기 월간 예측 보고서", title_style)
    subtitle = Paragraph(f"{year}년 {month}월", subtitle_style)
    elements.append(title)
    elements.append(subtitle)
    
    # 구분선 추가
    line_drawing = Drawing(170*mm, 1*mm)
    line = Line(0, 0, 340*mm, 0)
    line.strokeColor = colors.HexColor('#1a1a1a')
    line.strokeWidth = 0.5
    line_drawing.add(line)
    elements.append(line_drawing)
    elements.append(Spacer(1, 3*mm))
    
    # 2. 요약 섹션
    summary_title = Paragraph("요약", section_title_style)
    elements.append(summary_title)
    
    # 요약 박스 데이터
    summary = dashboard_data.summary
    change_direction = "증가" if summary.previous_month_change > 0 else "감소"
    
    summary_bullets = [
        f"• {month}월 해양쓰레기 유입량 전월 대비 {abs(summary.previous_month_change):.1f}% {change_direction}",
        f"• 총 예상 유입량: {summary.total_predicted_amount:.0f}kg",
        f"• 위험 지역 {summary.high_risk_count}개소, 주의 지역 {summary.medium_risk_count}개소",
        f"• 즉시 조치 필요: {summary.immediate_action_count}개소"
    ]
    
    for bullet in summary_bullets:
        elements.append(Paragraph(bullet, body_style))
    
    elements.append(Spacer(1, 8*mm))
    
    # 3. 월간 유입량 추이 (그래프) + 위험 지역 현황 (테이블) - 가로 배치
    
    # 왼쪽: 월간 유입량 추이 그래프
    trend_title = Paragraph("월간 유입량 추이", section_title_style)
    trend_spacer = Spacer(1, 2*mm)
    
    # 그래프 생성 (80mm x 45mm)
    drawing = Drawing(80*mm, 45*mm)
    chart = HorizontalLineChart()
    chart.x = 3*mm
    chart.y = 5*mm
    chart.height = 38*mm
    chart.width = 72*mm
    
    # 데이터 설정 (6개월)
    months_data = dashboard_data.monthly_trends
    chart.data = [[t.total_amount for t in months_data]]
    
    # X축 설정 (월 이름)
    chart.categoryAxis.categoryNames = [t.month for t in months_data]
    chart.categoryAxis.labels.fontName = korean_font
    chart.categoryAxis.labels.fontSize = 7
    chart.categoryAxis.labels.angle = 45
    
    # Y축 설정
    chart.valueAxis.labels.fontName = korean_font
    chart.valueAxis.labels.fontSize = 7
    chart.valueAxis.valueMin = 0
    max_value = max([t.total_amount for t in months_data]) if months_data else 1000
    chart.valueAxis.valueMax = max_value * 1.2
    chart.valueAxis.valueStep = max_value / 5
    
    # 선 스타일
    chart.lines[0].strokeColor = colors.HexColor('#4A90E2')
    chart.lines[0].strokeWidth = 2
    chart.lines[0].symbol = None
    
    # 그리드
    chart.categoryAxis.visibleGrid = True
    chart.valueAxis.visibleGrid = True
    chart.categoryAxis.gridStrokeColor = colors.HexColor('#E0E0E0')
    chart.valueAxis.gridStrokeColor = colors.HexColor('#E0E0E0')
    
    drawing.add(chart)
    
    # 오른쪽: 위험 지역 현황 테이블
    risk_title = Paragraph("위험 지역 현황", section_title_style)
    risk_spacer = Spacer(1, 2*mm)
    
    # 테이블 헤더
    risk_table_data = [
        ['지역', '예측량', '위험도', '조치']
    ]
    
    # 상위 5개 위험 지역만 표시
    for area in dashboard_data.risk_areas[:5]:
        risk_table_data.append([
            area.beach_name,
            f"{area.predicted_amount:.0f}kg",
            area.risk_level.value,
            area.action_required.value
        ])
    
    # 테이블 생성 (80mm 너비로 조정, 행 높이 지정으로 전체 높이 맞춤)
    risk_table = Table(
        risk_table_data, 
        colWidths=[21*mm, 19*mm, 17*mm, 23*mm],  # 총 80mm
        rowHeights=[8*mm] + [8*mm] * 5  # 헤더 7mm + 데이터 행 7mm x 5 = 총 42mm
    )
    risk_table.setStyle(TableStyle([
        # 헤더 스타일
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4A90E2')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), korean_font),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
        
        # 데이터 행 스타일
        ('FONTNAME', (0, 1), (-1, -1), korean_font),
        ('FONTSIZE', (0, 1), (-1, -1), 7),
        ('ALIGN', (0, 1), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 1), (-1, -1), 'MIDDLE'),
        
        # 격자선
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        
        # 교대 행 배경색
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F5F5F5')])
    ]))
    
    # 제목과 Spacer와 내용을 묶어서 2열 테이블로 배치
    combined_data = [
        [trend_title, risk_title],
        [trend_spacer, risk_spacer],
        [drawing, risk_table]
    ]
    
    combined_table = Table(combined_data, colWidths=[85*mm, 85*mm])
    combined_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    
    elements.append(combined_table)
    elements.append(Spacer(1, 6*mm))
    
    # 4. 방문객 통계 그래프 (가로로 길게)
    visitor_title = Paragraph("제주 해안별 월별 방문객 추이 (2024.01 - 2025.10)", section_title_style)
    elements.append(visitor_title)
    elements.append(Spacer(1, 2*mm))
    
    # 방문객 데이터를 지역별로 정리
    visitor_by_region = {}
    all_months = set()
    
    for stat in dashboard_data.visitor_stats:
        if stat.region not in visitor_by_region:
            visitor_by_region[stat.region] = {}
        visitor_by_region[stat.region][stat.year_month] = stat.visitor
        all_months.add(stat.year_month)
    
    # 월 정렬
    sorted_months = sorted(list(all_months))
    
    # 차트 데이터 구성 (각 지역별 라인)
    chart_data = []
    region_names = []
    
    for region in sorted(visitor_by_region.keys()):
        region_data = []
        for month in sorted_months:
            value = visitor_by_region[region].get(month, 0)
            region_data.append(value)
        chart_data.append(region_data)
        region_names.append(region)
    
    # 방문객 그래프 생성 (가로로 길게: 170mm x 55mm)
    visitor_drawing = Drawing(170*mm, 60*mm)
    visitor_chart = HorizontalLineChart()
    visitor_chart.x = 10*mm
    visitor_chart.y = 8*mm
    visitor_chart.height = 44*mm
    visitor_chart.width = 150*mm
    
    # 데이터 설정
    visitor_chart.data = chart_data
    
    # X축 설정 (월 레이블)
    month_labels = [m.split('-')[1] + '월' for m in sorted_months]
    visitor_chart.categoryAxis.categoryNames = month_labels
    visitor_chart.categoryAxis.labels.fontName = korean_font
    visitor_chart.categoryAxis.labels.fontSize = 6
    visitor_chart.categoryAxis.labels.angle = 45
    
    # Y축 설정
    visitor_chart.valueAxis.labels.fontName = korean_font
    visitor_chart.valueAxis.labels.fontSize = 7
    visitor_chart.valueAxis.valueMin = 0
    
    if chart_data:
        all_values = [val for line in chart_data for val in line]
        max_visitor = max(all_values) if all_values else 100000
        visitor_chart.valueAxis.valueMax = max_visitor * 1.1
        visitor_chart.valueAxis.valueStep = max_visitor / 5
    
    # 각 라인 스타일 설정 (다양한 색상)
    line_colors = [
        colors.HexColor('#4A90E2'),  # 파란색
        colors.HexColor('#E24A4A'),  # 빨간색
        colors.HexColor('#4AE290'),  # 초록색
        colors.HexColor('#E2904A'),  # 주황색
        colors.HexColor('#904AE2'),  # 보라색
        colors.HexColor('#E2E24A'),  # 노란색
        colors.HexColor('#4AE2E2'),  # 청록색
        colors.HexColor('#E24AE2'),  # 마젠타
        colors.HexColor('#90E24A'),  # 연두색
    ]
    
    for i in range(len(chart_data)):
        visitor_chart.lines[i].strokeColor = line_colors[i % len(line_colors)]
        visitor_chart.lines[i].strokeWidth = 1.5
        visitor_chart.lines[i].symbol = None
    
    # 그리드
    visitor_chart.categoryAxis.visibleGrid = True
    visitor_chart.valueAxis.visibleGrid = True
    visitor_chart.categoryAxis.gridStrokeColor = colors.HexColor('#E0E0E0')
    visitor_chart.valueAxis.gridStrokeColor = colors.HexColor('#E0E0E0')
    
    visitor_drawing.add(visitor_chart)
    
    # 범례 추가 (차트 오른쪽)
    legend_x = 162*mm
    legend_y = 48*mm
    for i, region in enumerate(region_names):
        # 색상 박스
        visitor_drawing.add(Line(legend_x, legend_y - i*4*mm, legend_x + 3*mm, legend_y - i*4*mm,
                                strokeColor=line_colors[i % len(line_colors)], strokeWidth=2))
        # 텍스트
        from reportlab.graphics.shapes import String
        visitor_drawing.add(String(legend_x + 4*mm, legend_y - i*4*mm - 1*mm, region,
                                   fontName=korean_font, fontSize=6, fillColor=colors.black))
    
    elements.append(visitor_drawing)
    elements.append(Spacer(1, 4*mm))
    
    # 5. 분석 섹션
    analysis_title = Paragraph("분석", section_title_style)
    elements.append(analysis_title)
    
    # 분석 내용 생성
    analysis_items = []
    
    if summary.high_risk_count > 0:
        analysis_items.append(
            f"현재 {summary.high_risk_count}개 지역이 높은 위험도를 보이고 있으며, "
            f"즉각적인 수거 작업이 필요합니다."
        )
    
    if summary.previous_month_change > 5:
        analysis_items.append(
            f"전월 대비 {summary.previous_month_change:.1f}% 증가로 유입량이 크게 증가했습니다. "
            f"기상 조건과 해류 패턴의 변화가 주요 원인으로 분석됩니다."
        )
    elif summary.previous_month_change < -5:
        analysis_items.append(
            f"전월 대비 {abs(summary.previous_month_change):.1f}% 감소로 개선 추세를 보이고 있습니다."
        )
    
    # 가장 위험한 지역 언급
    if dashboard_data.risk_areas:
        top_risk = dashboard_data.risk_areas[0]
        analysis_items.append(
            f"{top_risk.beach_name} 지역이 {top_risk.predicted_amount:.0f}kg으로 "
            f"가장 높은 유입량이 예상되며, {top_risk.action_required} 조치가 필요합니다."
        )
    
    for item in analysis_items:
        elements.append(Paragraph(f"• {item}", body_style))
        elements.append(Spacer(1, 2*mm))
    
    # 페이지 하단에 고정될 footer 함수 정의
    def add_page_footer(canvas, doc):
        """모든 페이지 하단에 보고서 생성일 추가"""
        canvas.saveState()
        footer_text = f"보고서 생성일: {date.today().strftime('%Y년 %m월 %d일')}"
        canvas.setFont(korean_font, 8)
        canvas.setFillColor(colors.grey)
        # 페이지 하단 중앙에 배치 (하단에서 10mm)
        canvas.drawCentredString(A4[0] / 2, 10*mm, footer_text)
        canvas.restoreState()
    
    # PDF 생성 (footer를 페이지 하단에 고정)
    doc.build(elements, onFirstPage=add_page_footer, onLaterPages=add_page_footer)


@router.post("/monthly")
async def generate_monthly_report(
    request: ReportRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    월간 해양쓰레기 예측 보고서 PDF 생성
    
    **인증 필요**: Authorization 헤더에 Bearer 토큰 필요
    
    대시보드 데이터를 기반으로 PDF 형식의 월간 보고서를 생성합니다.
    
    - **organization_name**: 발행 기관명 (기본값: "해양환경공단")
    """
    try:
        # 대시보드 데이터 가져오기
        dashboard_data = await get_dashboard(db)
        
        # PDF 생성을 위한 버퍼
        buffer = BytesIO()
        
        # 로고 경로 구성 (resources 폴더의 고정 로고 사용)
        logo_full_path = os.path.join(
            os.path.dirname(__file__), '..', '..', 'resources', 'Emblem_of_the_Government_of_the_Republic_of_Korea.png'
        )
        logo_full_path = os.path.abspath(logo_full_path)
        
        # PDF 생성
        create_pdf_report(
            dashboard_data, 
            buffer, 
            organization_name=request.organization_name,
            logo_path=logo_full_path
        )
        
        # 버퍼 위치를 처음으로 이동
        buffer.seek(0)
        
        # PDF 파일명
        year, month = dashboard_data.target_month.split('-')
        filename = f"제주_해양쓰레기_월간_예측_보고서_{year}년_{month}월.pdf"
        encoded_filename = quote(filename)
        
        # Response 반환
        return Response(
            content=buffer.getvalue(),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF 생성 실패: {str(e)}")
