from fpdf import FPDF

def create_pdf_report(df, total_effort, team_capacity):

    pdf = FPDF()
    pdf.add_page()

    pdf.set_font("Arial", size=12)

    pdf.cell(200,10,"AI Sprint Report",ln=True)

    pdf.cell(200,10,f"Total Tasks: {len(df)}",ln=True)
    pdf.cell(200,10,f"Team Capacity: {team_capacity}",ln=True)
    pdf.cell(200,10,f"Total Effort: {total_effort}",ln=True)

    pdf.cell(200,10,"",ln=True)

    pdf.cell(200,10,"High Risk Tasks:",ln=True)

    for index,row in df.iterrows():
        if row["risk_score"] >= 3:
            pdf.cell(200,10,f'{row["key"]} - Risk:{row["risk_score"]}',ln=True)

    pdf.output("sprint_report.pdf")

    print("PDF report created: sprint_report.pdf")