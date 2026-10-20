import os
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls

def set_cell_background(cell, fill_hex):
    tcPr = cell._element.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    tcPr.append(shd)

def set_cell_margins(cell, top=100, bottom=100, left=110, right=110):
    tcPr = cell._element.get_or_add_tcPr()
    tcMar = parse_xml(
        f'<w:tcMar {nsdecls("w")}>'
        f'<w:top w:w="{top}" w:type="dxa"/>'
        f'<w:bottom w:w="{bottom}" w:type="dxa"/>'
        f'<w:left w:w="{left}" w:type="dxa"/>'
        f'<w:right w:w="{right}" w:type="dxa"/>'
        f'</w:tcMar>'
    )
    tcPr.append(tcMar)

def set_table_borders(table, color="CBD5E0", sz="4", val="single"):
    tblPr = table._element.xpath('w:tblPr')
    if tblPr:
        borders = parse_xml(
            f'<w:tblBorders {nsdecls("w")}>'
            f'<w:top w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
            f'<w:bottom w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
            f'<w:insideH w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
            f'<w:insideV w:val="none"/>'
            f'<w:left w:val="none"/>'
            f'<w:right w:val="none"/>'
            f'</w:tblBorders>'
        )
        tblPr[0].append(borders)

def append_chumbo_equivalencia(doc_path):
    doc = Document(doc_path)
    
    COLOR_PRIMARY = RGBColor(26, 54, 93)      # #1A365D
    COLOR_SECONDARY = RGBColor(43, 108, 176)  # #2B6CB0
    COLOR_TEXT = RGBColor(45, 55, 72)         # #2D3748
    HEX_PRIMARY = "1A365D"
    HEX_ALT_ROW = "F7FAFC"
    HEX_ACCENT_BG = "EBF8FF"

    p_title = doc.add_paragraph()
    p_title.paragraph_format.space_before = Pt(16)
    p_title.paragraph_format.space_after = Pt(4)
    p_title.paragraph_format.keep_with_next = True
    r = p_title.add_run("7.7 Diretriz Mandatória para Substituição por Bateria Selada (Chumbo 12 V em Série)")
    r.font.bold = True
    r.font.size = Pt(12)
    r.font.color.rgb = COLOR_PRIMARY

    p_desc = doc.add_paragraph()
    p_desc.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p_desc.paragraph_format.space_after = Pt(6)
    p_desc.paragraph_format.line_spacing = 1.15
    r_d = p_desc.add_run(
        "Se em campo for necessário optar por baterias seladas de Chumbo-Ácido (VRLA AGM ou Gel) ao invés da bateria de Lítio LiFePO4, "
        "é mandatório compreender a mudança de capacidade necessária para manter as premissas originais de autonomia do projeto. "
        "Como a bateria de chumbo permite apenas 50% de profundidade de descarga (DoD) sem sofrer degradação acelerada de vida útil "
        "(contra 90% do lítio), existem dois caminhos de projeto:"
    )
    r_d.font.color.rgb = COLOR_TEXT

    eq_data = [
        ("Cenário de Armazenamento", "Configuração do Banco (24 V)", "Energia Bruta Total", "Energia Útil (DoD)", "Autonomia sem Sol (6 W)", "Avaliação Técnica"),
        ("Referência Original (Lítio)", "1x Bateria LiFePO4 50 Ah 24 V (Unipower)", "1.280 Wh nominais", "1.152 Wh úteis (90% DoD)", "8,0 dias (192 h)", "Padrão Ouro (15,5 kg / 1 bloco)"),
        ("Opção Chumbo 50 Ah (Substituição 1:1)", "2x Baterias 12 V 50 Ah em série (24 V)", "1.200 Wh nominais", "600 Wh úteis (50% DoD)", "4,1 dias (100 h)", "Viável (> 4 dias / 25 a 30 kg)"),
        ("Opção Chumbo 100 Ah (EQUIVALÊNCIA PLENA)", "2x Baterias 12 V 100-105 Ah em série (24 V)", "2.400 a 2.520 Wh nominais", "1.200 a 1.260 Wh úteis (50% DoD)", "8,3 a 8,7 dias (200 h)", "IGUAL AO LÍTIO (55 a 60 kg)")
    ]

    table_eq = doc.add_table(rows=len(eq_data), cols=6)
    table_eq.alignment = WD_TABLE_ALIGNMENT.CENTER
    table_eq.autofit = False
    set_table_borders(table_eq, color="CBD5E0")

    col_w_eq = [Inches(1.5), Inches(1.5), Inches(1.1), Inches(1.1), Inches(1.1), Inches(1.2)]

    for row_idx, row in enumerate(table_eq.rows):
        is_header = (row_idx == 0)
        vals = eq_data[row_idx]
        for col_idx, cell in enumerate(row.cells):
            cell.width = col_w_eq[col_idx]
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            set_cell_margins(cell, top=70, bottom=70, left=70, right=70)
            
            p = cell.paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.space_before = Pt(0)
            
            if is_header:
                set_cell_background(cell, HEX_PRIMARY)
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER if col_idx >= 2 else WD_ALIGN_PARAGRAPH.LEFT
                run = p.add_run(vals[col_idx])
                run.font.bold = True
                run.font.color.rgb = RGBColor(255, 255, 255)
            else:
                bg = HEX_ACCENT_BG if row_idx == 3 else (HEX_ALT_ROW if row_idx % 2 == 1 else "FFFFFF")
                set_cell_background(cell, bg)
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER if col_idx in [2, 3, 4] else WD_ALIGN_PARAGRAPH.LEFT
                run = p.add_run(vals[col_idx])
                if row_idx == 3 or col_idx == 0:
                    run.font.bold = True
                    run.font.color.rgb = COLOR_PRIMARY if row_idx == 3 else COLOR_TEXT
                else:
                    run.font.color.rgb = COLOR_TEXT

    doc.add_paragraph().paragraph_format.space_after = Pt(6)

    p_models = doc.add_paragraph()
    p_models.paragraph_format.space_before = Pt(8)
    p_models.paragraph_format.space_after = Pt(4)
    p_models.paragraph_format.keep_with_next = True
    rm = p_models.add_run("Modelos de Baterias Seladas Homologados para Equivalência Plena (Comprar 2 unidades de 12 V 100 Ah a 105 Ah):")
    rm.font.bold = True
    rm.font.size = Pt(11)
    rm.font.color.rgb = COLOR_PRIMARY

    models_data = [
        ("Modelo Homologado (100Ah)", "Capacidade & Fabricante", "Dimensões Unitárias (C × L × A)", "Peso Total do Par (24 V)", "Observação Técnica para Campo"),
        ("Freedom DF2000", "12 V  •  105 Ah (C20) / 115 Ah (C100)\nClarios / Johnson Controls", "330 × 172 × 240 mm", "≈ 54,2 kg o par (27,1 kg cada)", "Líder em telecom e solar. Grade PowerFrame de alta durabilidade."),
        ("Moura Clean 12MF105", "12 V  •  105 Ah (C20)\nAcumuladores Moura", "330 × 172 × 244 mm", "≈ 54,6 kg o par (27,3 kg cada)", "Linha Nano desenvolvida para aguentar altas temperaturas no campo (até 60°C)."),
        ("Unipower UP121000", "12 V  •  100 Ah (C10) / 110 Ah (C20)\nUnicoba / Unipower", "331 × 173 × 213 mm", "≈ 61,6 kg o par (30,8 kg cada)", "Tecnologia VRLA AGM 100% selada e à prova de vazamento.")
    ]

    table_m = doc.add_table(rows=len(models_data), cols=5)
    table_m.alignment = WD_TABLE_ALIGNMENT.CENTER
    table_m.autofit = False
    set_table_borders(table_m, color="CBD5E0")
    col_w_m = [Inches(1.8), Inches(1.8), Inches(1.3), Inches(1.1), Inches(1.5)]

    for row_idx, row in enumerate(table_m.rows):
        is_header = (row_idx == 0)
        vals = models_data[row_idx]
        for col_idx, cell in enumerate(row.cells):
            cell.width = col_w_m[col_idx]
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            set_cell_margins(cell, top=70, bottom=70, left=70, right=70)
            
            p = cell.paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.space_before = Pt(0)
            
            if is_header:
                set_cell_background(cell, HEX_PRIMARY)
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER if col_idx in [1, 2, 3] else WD_ALIGN_PARAGRAPH.LEFT
                run = p.add_run(vals[col_idx])
                run.font.bold = True
                run.font.color.rgb = RGBColor(255, 255, 255)
            else:
                bg = HEX_ALT_ROW if row_idx % 2 == 1 else "FFFFFF"
                set_cell_background(cell, bg)
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER if col_idx in [2, 3] else WD_ALIGN_PARAGRAPH.LEFT
                run = p.add_run(vals[col_idx])
                if col_idx == 0:
                    run.font.bold = True
                    run.font.color.rgb = COLOR_PRIMARY
                else:
                    run.font.color.rgb = COLOR_TEXT

    doc.add_paragraph().paragraph_format.space_after = Pt(6)

    def add_bullet(title_prefix, text):
        p = doc.add_paragraph(style='List Bullet')
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.line_spacing = 1.15
        rb = p.add_run(title_prefix)
        rb.font.bold = True
        rb.font.color.rgb = COLOR_PRIMARY
        r = p.add_run(text)
        r.font.color.rgb = COLOR_TEXT

    add_bullet(
        "Regra de Ouro da Equivalência: ",
        "Para ter exatamente a MESMA autonomia de 8 dias da bateria de lítio 50 Ah 24 V, DEVE-SE COMPRAR 2 BATERIAS SELADAS DE 12 V 100 Ah (ou 105 Ah) para ligar em série. "
        "A compra de baterias de 50 Ah seladas também funciona perfeitamente, mas a autonomia será de 4,1 dias ininterruptos."
    )
    add_bullet(
        "Ajuste Mandatório na Controladora EPEVER: ",
        "Ao conectar baterias seladas de chumbo (sejam de 50 Ah ou de 100 Ah), mudar obrigatoriamente a chave/parâmetro de seleção da bateria de 'LFP' (Lítio) para 'AGM/GEL' (Chumbo selado). "
        "Isso ajusta a tensão de absorção para 28,8 V, flutuação para 27,4 V e corte de proteção por subtensão (LVD) para 22,0 V."
    )
    add_bullet(
        "Acessórios de Montagem em Campo: ",
        "Incluir na compra 1 cabo ponte de interligação flexível de 25 cm (bitola mínima 6 mm² ou 10 mm²) com terminais olhais M6/M8 prensados para ligar o polo (+) da bateria 1 no polo (-) da bateria 2. "
        "Verificar também o suporte mecânico no solo/poste, pois o par de 100 Ah pesa aproximadamente 55 kg a 60 kg."
    )

    doc.save(doc_path)
    print(f"Sucesso: Adicionada diretriz de equivalência de baterias seladas a {doc_path}")

def rebuild_resumo_executivo(output_path):
    doc = Document()

    for section in doc.sections:
        section.top_margin = Inches(0.8)
        section.bottom_margin = Inches(0.8)
        section.left_margin = Inches(0.8)
        section.right_margin = Inches(0.8)

    COLOR_PRIMARY = RGBColor(26, 54, 93)      # #1A365D - Azul Marinho
    COLOR_SECONDARY = RGBColor(43, 108, 176)  # #2B6CB0 - Azul Técnico
    COLOR_TEXT = RGBColor(45, 55, 72)         # #2D3748 - Chumbo
    COLOR_MUTED = RGBColor(113, 128, 150)     # #718096 - Cinza Médio

    HEX_PRIMARY = "1A365D"
    HEX_ALT_ROW = "F7FAFC"
    HEX_ACCENT_BG = "EBF8FF"

    normal_style = doc.styles['Normal']
    normal_style.font.name = 'Calibri'
    normal_style.font.size = Pt(10)
    normal_style.font.color.rgb = COLOR_TEXT
    normal_style.paragraph_format.line_spacing = 1.15
    normal_style.paragraph_format.space_after = Pt(3)

    # Titulo
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_title.paragraph_format.space_before = Pt(6)
    p_title.paragraph_format.space_after = Pt(2)
    run_title = p_title.add_run("Estudo Executivo — Sistema Solar Off-Grid 24 V")
    run_title.font.name = 'Calibri'
    run_title.font.size = Pt(20)
    run_title.font.bold = True
    run_title.font.color.rgb = COLOR_PRIMARY

    p_sub = doc.add_paragraph()
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_sub.paragraph_format.space_after = Pt(8)
    run_sub = p_sub.add_run("Dimensionamento, Instalação e Suprimentos (Conjunto FertiBox / MAGX / EPEVER)")
    run_sub.font.name = 'Calibri'
    run_sub.font.size = Pt(12)
    run_sub.font.bold = True
    run_sub.font.color.rgb = COLOR_SECONDARY

    p_meta = doc.add_paragraph()
    p_meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_meta.paragraph_format.space_after = Pt(14)
    run_meta = p_meta.add_run("Solinftec • Engenharia de Hardware & Fertirrigação LATAM • Documento Técnico Consolidado")
    run_meta.font.size = Pt(9)
    run_meta.font.color.rgb = COLOR_MUTED
    run_meta.font.italic = True

    def add_sec(num, title):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(12)
        p.paragraph_format.space_after = Pt(3)
        p.paragraph_format.keep_with_next = True
        r_num = p.add_run(f"{num}. ")
        r_num.font.bold = True
        r_num.font.size = Pt(11.5)
        r_num.font.color.rgb = COLOR_SECONDARY
        r_t = p.add_run(title)
        r_t.font.bold = True
        r_t.font.size = Pt(11.5)
        r_t.font.color.rgb = COLOR_PRIMARY

    def add_p(text, bold_prefix=None, space_after=3):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.space_after = Pt(space_after)
        p.paragraph_format.line_spacing = 1.15
        if bold_prefix:
            rb = p.add_run(bold_prefix)
            rb.font.bold = True
            rb.font.color.rgb = COLOR_PRIMARY
        r = p.add_run(text)
        r.font.color.rgb = COLOR_TEXT
        return p

    def add_b(title_prefix, text):
        p = doc.add_paragraph(style='List Bullet')
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.space_after = Pt(2.5)
        p.paragraph_format.line_spacing = 1.15
        rb = p.add_run(title_prefix)
        rb.font.bold = True
        rb.font.color.rgb = COLOR_PRIMARY
        r = p.add_run(text)
        r.font.color.rgb = COLOR_TEXT
        return p

    # 1. DADOS DE ENTRADA
    add_sec("1", "Dados de Entrada do Projeto")
    add_p("Parâmetros operacionais do sistema solar off-grid para o conjunto FertiBox:")

    t1_data = [
        ("Parâmetro de Entrada", "Especificação Adotada", "Observação Técnica"),
        ("Consumo da Carga", "6,0 W contínuo (24 horas ininterruptas)", "144 Wh/dia (0,144 kWh/dia)"),
        ("Tensão Nominal do Sistema", "24 V DC nominal (25,6 V LiFePO4)", "Padrão FertiBox / Computador MAGX"),
        ("Arranjo Fotovoltaico", "2 painéis de 100 W (200 Wp totais)", "Ligados em série (Silício Mono ou Poli)"),
        ("Bateria de Referência (Lítio)", "50 Ah LiFePO4 24 V (Unipower UPLFP24-50)", "1.280 Wh nominais / 1.152 Wh úteis (DoD 90%)"),
        ("Bateria Alternativa (Chumbo Selado)", "2x 12 V 100 Ah em série (Equivalente) ou 2x 50 Ah", "50% DoD máx. (1.200 Wh úteis c/ 100 Ah ou 600 Wh c/ 50 Ah)"),
        ("Controladora de Carga", "EPEVER (24 V / 10 A a 15 A)", "Curva programável LFP (Lítio) ou AGM/GEL (Chumbo)"),
        ("Computador de Bordo", "Solinftec MAGX", "Telemetria, sensores e comunicação"),
        ("Irradiação de Referência", "4,5 Horas de Sol Pleno (HSP)", "Base de dimensionamento Brasil e LATAM")
    ]

    t1 = doc.add_table(rows=len(t1_data), cols=3)
    t1.alignment = WD_TABLE_ALIGNMENT.CENTER
    t1.autofit = False
    set_table_borders(t1, color="CBD5E0")
    col_w1 = [Inches(2.3), Inches(2.7), Inches(2.2)]

    for row_idx, row in enumerate(t1.rows):
        is_header = (row_idx == 0)
        vals = t1_data[row_idx]
        for col_idx, cell in enumerate(row.cells):
            cell.width = col_w1[col_idx]
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            set_cell_margins(cell, top=60, bottom=60, left=70, right=70)
            p = cell.paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.space_before = Pt(0)
            if is_header:
                set_cell_background(cell, HEX_PRIMARY)
                run = p.add_run(vals[col_idx])
                run.font.bold = True
                run.font.color.rgb = RGBColor(255, 255, 255)
            else:
                bg = HEX_ALT_ROW if row_idx % 2 == 1 else "FFFFFF"
                set_cell_background(cell, bg)
                run = p.add_run(vals[col_idx])
                if col_idx == 0:
                    run.font.bold = True
                    run.font.color.rgb = COLOR_PRIMARY
                else:
                    run.font.color.rgb = COLOR_TEXT

    # 2. DIMENSIONAMENTO E AUTONOMIA
    add_sec("2", "Dimensionamento da Geração e Autonomia por Tipo de Bateria")
    add_b("Consumo Diário: ", "6 W × 24 h = 144 Wh/dia (0,144 kWh/dia).")
    add_b("Geração Real Média Diária (2 × 100 W): ", "200 Wp × 4,5 h × 78% rendimento ≈ 700 Wh/dia (margem de 4,8× sobre o consumo).")
    add_p("A autonomia sem sol varia radicalmente dependendo da química da bateria (limite de 50% DoD no chumbo vs. 90% no lítio):")

    t_auto = [
        ("Tecnologia de Bateria Adotada", "Capacidade do Banco (24 V)", "Energia Útil", "Autonomia sem Sol (6 W)", "Avaliação Técnica"),
        ("Lítio LiFePO4 (Unipower UPLFP24-50)", "50 Ah 24 V (1 bloco)", "1.152 Wh (90% DoD)", "8,0 dias (192 horas)", "Ideal / Padrão Ouro (15,5 kg)"),
        ("Chumbo Selado 50 Ah (Substituição Direta)", "2x 12 V 50 Ah em série", "600 Wh (50% DoD)", "4,1 dias (100 horas)", "Viável (> norma de 3 a 4 dias)"),
        ("Chumbo Selado 100 Ah (EQUIVALÊNCIA PLENA)", "2x 12 V 100-105 Ah em série", "1.200 a 1.260 Wh (50% DoD)", "8,3 a 8,7 dias (200 h)", "IGUAL AO LÍTIO (55 a 60 kg)")
    ]

    ta = doc.add_table(rows=len(t_auto), cols=5)
    ta.alignment = WD_TABLE_ALIGNMENT.CENTER
    ta.autofit = False
    set_table_borders(ta, color="CBD5E0")
    col_wa = [Inches(1.8), Inches(1.4), Inches(1.1), Inches(1.4), Inches(1.5)]

    for row_idx, row in enumerate(ta.rows):
        is_header = (row_idx == 0)
        vals = t_auto[row_idx]
        for col_idx, cell in enumerate(row.cells):
            cell.width = col_wa[col_idx]
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            set_cell_margins(cell, top=60, bottom=60, left=70, right=70)
            p = cell.paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.space_before = Pt(0)
            if is_header:
                set_cell_background(cell, HEX_PRIMARY)
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER if col_idx in [1, 2, 3] else WD_ALIGN_PARAGRAPH.LEFT
                run = p.add_run(vals[col_idx])
                run.font.bold = True
                run.font.color.rgb = RGBColor(255, 255, 255)
            else:
                bg = HEX_ACCENT_BG if row_idx == 3 else (HEX_ALT_ROW if row_idx % 2 == 1 else "FFFFFF")
                set_cell_background(cell, bg)
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER if col_idx in [1, 2, 3] else WD_ALIGN_PARAGRAPH.LEFT
                run = p.add_run(vals[col_idx])
                if row_idx == 3 or col_idx == 0:
                    run.font.bold = True
                    run.font.color.rgb = COLOR_PRIMARY if row_idx == 3 else COLOR_TEXT
                else:
                    run.font.color.rgb = COLOR_TEXT

    # 3. FAIXA DE CONSUMO SEGURO
    add_sec("3", "Faixa de Consumo Seguro (Expansão de Carga)")
    add_p("Comportamento do sistema ao variar a potência contínua, comparando a autonomia do Lítio 50 Ah vs. Chumbo Equivalente 100 Ah vs. Chumbo 50 Ah:")

    t2_data = [
        ("Potência Carga", "Consumo Diário", "Sobra p/ Recarga", "Autonomia Lítio 50Ah / Chumbo 100Ah", "Autonomia Chumbo 50Ah", "Status"),
        ("6 W (Base)", "144 Wh/dia", "≈ 556 Wh/dia (4,8×)", "8,0 a 8,5 dias (192 h)", "4,1 dias (100 h)", "Superdimensionado"),
        ("12 W", "288 Wh/dia", "≈ 412 Wh/dia (2,4×)", "4,0 a 4,2 dias (96 h)", "2,1 dias (50 h)", "Muito Seguro"),
        ("15 W", "360 Wh/dia", "≈ 340 Wh/dia (1,9×)", "3,2 a 3,4 dias (77 h)", "1,7 dia (40 h)", "Padrão Ideal"),
        ("20 W (Teto Seguro)", "480 Wh/dia", "≈ 220 Wh/dia (1,45×)", "2,4 a 2,5 dias (58 h)", "1,25 dia (30 h)", "Limite Recomendado"),
        ("24 W (Emergência)", "576 Wh/dia", "≈ 124 Wh/dia (1,2×)", "2,0 dias (48 h)", "1,0 dia (24 h)", "Alerta Técnico")
    ]

    t2 = doc.add_table(rows=len(t2_data), cols=6)
    t2.alignment = WD_TABLE_ALIGNMENT.CENTER
    t2.autofit = False
    set_table_borders(t2, color="CBD5E0")
    col_w2 = [Inches(1.1), Inches(1.1), Inches(1.3), Inches(1.5), Inches(1.2), Inches(1.0)]

    for row_idx, row in enumerate(t2.rows):
        is_header = (row_idx == 0)
        vals = t2_data[row_idx]
        for col_idx, cell in enumerate(row.cells):
            cell.width = col_w2[col_idx]
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            set_cell_margins(cell, top=60, bottom=60, left=60, right=60)
            p = cell.paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.space_before = Pt(0)
            if is_header:
                set_cell_background(cell, HEX_PRIMARY)
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER if col_idx in [0, 1, 2, 3, 4] else WD_ALIGN_PARAGRAPH.LEFT
                run = p.add_run(vals[col_idx])
                run.font.bold = True
                run.font.color.rgb = RGBColor(255, 255, 255)
            else:
                bg = HEX_ACCENT_BG if row_idx == 4 else (HEX_ALT_ROW if row_idx % 2 == 1 else "FFFFFF")
                set_cell_background(cell, bg)
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER if col_idx in [0, 1, 2, 3, 4] else WD_ALIGN_PARAGRAPH.LEFT
                run = p.add_run(vals[col_idx])
                if row_idx == 4 or col_idx == 0:
                    run.font.bold = True
                    run.font.color.rgb = COLOR_PRIMARY
                else:
                    run.font.color.rgb = COLOR_TEXT

    # 4. VALIDAÇÃO REGIONAL
    add_sec("4", "Validação Regional: Foco em Colômbia e Costa Rica")
    add_b("Colômbia (Valle del Cauca / Cali, Meta, Tolima): ", "HSP médio de 4,3 a 5,0 h gerando de 670 a 780 Wh/dia. Geração 4,5× a 5,4× superior ao consumo.")
    add_b("Costa Rica (Guanacaste, San Carlos, Limón): ", "No mês mais chuvoso do Caribe (HSP piso de ≈ 3,8 h), os painéis produzem 590 Wh/dia (mais de 4,1× o consumo da FertiBox).")
    add_b("Inclinação de Instalação: ", "10° a 15° voltado ao Norte/Sul para autolimpeza pela chuva, evitando acúmulo de poeira e defensivos agrícolas.")

    # 5. BOM
    add_sec("5", "Lista Consolidada de Materiais (BOM de Campo)")
    t3_data = [
        ("Item / Subsistema", "Qtd.", "Especificação Técnica Recomendada", "Finalidade Operacional"),
        ("FertiBox Completa", "1 kit", "Gabinete estanque IP66 + MAGX + EPEVER + Chicote", "Núcleo de controle, recarga e telemetria"),
        ("Módulos Fotovoltaicos", "2 un.", "100 Wp cada (Mono/Poli-Si) com conectores MC4", "Geração de energia solar (200 Wp em série)"),
        ("Bateria LiFePO4 (ou Chumbo)", "1 un. Lítio ou 2x Chumbo", "50 Ah 24 V Lítio OU 2x 12V 100Ah Chumbo (Equivalente)", "Armazenamento e sustentação ininterrupta"),
        ("Estrutura de Fixação", "1 kit", "Alumínio anodizado p/ montagem em poste ou solo", "Fixação mecânica com inclinação de 10° a 15°"),
        ("Proteções Elétricas DC", "1 kit", "Disjuntor solar (10-16A) + Fusível bateria + DPS DC", "Proteção contra curto-circuito e surtos de raios"),
        ("Acessórios de Vedação e Cabo", "1 kit", "Prensa-cabos estanques + 2 sachês sílica gel + Cabo ponte 6mm²", "Vedação IP66 e ponte de ligação em série (se chumbo)")
    ]

    t3 = doc.add_table(rows=len(t3_data), cols=4)
    t3.alignment = WD_TABLE_ALIGNMENT.CENTER
    t3.autofit = False
    set_table_borders(t3, color="CBD5E0")
    col_w3 = [Inches(1.8), Inches(1.0), Inches(2.5), Inches(1.9)]

    for row_idx, row in enumerate(t3.rows):
        is_header = (row_idx == 0)
        vals = t3_data[row_idx]
        for col_idx, cell in enumerate(row.cells):
            cell.width = col_w3[col_idx]
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            set_cell_margins(cell, top=60, bottom=60, left=70, right=70)
            p = cell.paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.space_before = Pt(0)
            if is_header:
                set_cell_background(cell, HEX_PRIMARY)
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER if col_idx == 1 else WD_ALIGN_PARAGRAPH.LEFT
                run = p.add_run(vals[col_idx])
                run.font.bold = True
                run.font.color.rgb = RGBColor(255, 255, 255)
            else:
                bg = HEX_ACCENT_BG if row_idx == 1 else (HEX_ALT_ROW if row_idx % 2 == 1 else "FFFFFF")
                set_cell_background(cell, bg)
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER if col_idx == 1 else WD_ALIGN_PARAGRAPH.LEFT
                run = p.add_run(vals[col_idx])
                if col_idx == 0:
                    run.font.bold = True
                    run.font.color.rgb = COLOR_PRIMARY
                else:
                    run.font.color.rgb = COLOR_TEXT

    # 6. MODELOS HOMOLOGADOS
    add_sec("6", "Modelos Homologados para Compras e Suprimentos")
    add_b("Bateria de LÍTIO (Opção Preferencial de Alta Durabilidade): ", "Unipower UPLFP24-50 (25,6 V / 50 Ah LiFePO4). Entrega 1.280 Wh nominais, formato slim vertical (395 × 110 × 293 mm), peso de apenas 15,5 kg e BMS inteligente com proteção total. Autonomia de 8,0 dias a 6 W. 100% compatível com perfil LiFePO4 da controladora EPEVER.")
    add_p("Baterias de CHUMBO-ÁCIDO SELADAS (Opção Alternativa — Comprar 2 unidades de 12 V em série):")

    t4_data = [
        ("Modelo Comercial Homologado", "Capacidade & Tensão", "Dimensões e Peso do Par (24 V)", "Autonomia a 6 W", "Perfil Operacional"),
        ("Freedom DF2000 (Clarios)", "12 V — 105 Ah (C20) / 115 Ah (C100)", "330 × 172 × 240 mm (≈ 54,2 kg o par)", "8,5 dias (204 h)", "EQUIVALÊNCIA PLENA AO LÍTIO"),
        ("Moura Clean 12MF105", "12 V — 105 Ah (C20)", "330 × 172 × 244 mm (≈ 54,6 kg o par)", "8,5 dias (204 h)", "EQUIVALÊNCIA PLENA AO LÍTIO (Nano 60°C)"),
        ("Unipower UP121000 AGM", "12 V — 100 Ah (C10) / 110 Ah (C20)", "331 × 173 × 213 mm (≈ 61,6 kg o par)", "8,3 dias (200 h)", "EQUIVALÊNCIA PLENA AO LÍTIO (AGM Selada)"),
        ("Freedom DF700 (Econômica)", "12 V — 50 Ah (C100) / 45 Ah (C20)", "210 × 175 × 175 mm (≈ 25,0 kg o par)", "4,1 dias (100 h)", "Substituição Direta Econômica (> 4 dias)"),
        ("Moura Clean 12MF45 / 12MF55", "12 V — 45 Ah / 55 Ah (C20)", "212 × 175 × 175 mm (≈ 26,0 kg o par)", "4,1 a 4,5 dias", "Substituição Direta Econômica (Nano)")
    ]

    t4 = doc.add_table(rows=len(t4_data), cols=5)
    t4.alignment = WD_TABLE_ALIGNMENT.CENTER
    t4.autofit = False
    set_table_borders(t4, color="CBD5E0")
    col_w4 = [Inches(1.8), Inches(1.5), Inches(1.6), Inches(1.1), Inches(1.2)]

    for row_idx, row in enumerate(t4.rows):
        is_header = (row_idx == 0)
        vals = t4_data[row_idx]
        for col_idx, cell in enumerate(row.cells):
            cell.width = col_w4[col_idx]
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            set_cell_margins(cell, top=60, bottom=60, left=70, right=70)
            p = cell.paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.space_before = Pt(0)
            if is_header:
                set_cell_background(cell, HEX_PRIMARY)
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER if col_idx in [1, 2, 3] else WD_ALIGN_PARAGRAPH.LEFT
                run = p.add_run(vals[col_idx])
                run.font.bold = True
                run.font.color.rgb = RGBColor(255, 255, 255)
            else:
                bg = HEX_ACCENT_BG if row_idx in [1, 2, 3] else (HEX_ALT_ROW if row_idx % 2 == 1 else "FFFFFF")
                set_cell_background(cell, bg)
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER if col_idx in [1, 2, 3] else WD_ALIGN_PARAGRAPH.LEFT
                run = p.add_run(vals[col_idx])
                if row_idx in [1, 2, 3] or col_idx == 0:
                    run.font.bold = True
                    run.font.color.rgb = COLOR_PRIMARY if row_idx in [1, 2, 3] else COLOR_TEXT
                else:
                    run.font.color.rgb = COLOR_TEXT

    add_p(
        "Ajuste Obrigatório na Controladora EPEVER: Ao optar por baterias seladas de chumbo (de 50 Ah ou 100 Ah), mudar a chave de seleção de bateria "
        "para 'AGM/GEL' (tensão de absorção em 28,8 V, flutuação em 27,4 V e corte LVD em 22,0 V). "
        "Adquirir junto 1 cabo de interligação de 25 cm (bitola 6 mm² ou 10 mm²) com terminais olhais para a ligação em série das duas baterias de 12 V.",
        bold_prefix="Diretriz de Instalação: ",
        space_after=6
    )

    doc.save(output_path)
    print(f"Sucesso: Resumo executivo consolidado com equivalência de chumbo gerado em {output_path}")

if __name__ == "__main__":
    estudo_file = r"c:\Users\Fernando Garcia\OneDrive - Tecsoil Automação e Sistemas S.A\Solinftec\Fertirigação\LATAM\Estudos\Avaliação para geração Solar.docx"
    bom_file = r"c:\Users\Fernando Garcia\OneDrive - Tecsoil Automação e Sistemas S.A\Solinftec\Fertirigação\LATAM\Estudos\Itens necessários para a instalação.docx"
    resumo_file = r"c:\Users\Fernando Garcia\OneDrive - Tecsoil Automação e Sistemas S.A\Solinftec\Fertirigação\LATAM\Estudos\Resumo Executivo — Dimensionamento e Instalação Solar FertiBox.docx"
    
    append_chumbo_equivalencia(estudo_file)
    append_chumbo_equivalencia(bom_file)
    rebuild_resumo_executivo(resumo_file)
