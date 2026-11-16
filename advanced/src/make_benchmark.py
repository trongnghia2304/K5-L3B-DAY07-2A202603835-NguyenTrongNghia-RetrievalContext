"""Write advanced/benchmark/questions.json (draft authored with AI help; reviewed by the student).

Each answerable question: id, split, group (one main group), question, expected_answer,
evidence = list of {page, kind, locator, values (numbers as printed), quote (optional)}, calc.
No-evidence questions: absence_reason + near_topic_pages.
Run:  python advanced/src/make_benchmark.py   then   python advanced/src/verify_benchmark.py
"""
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
Q: list[dict] = []


def E(page, kind, locator, values, quote=None):
    e = {"page": page, "kind": kind, "locator": locator, "values": values}
    if quote:
        e["quote"] = quote
    return e


def add(id, split, group, question, answer, evidence, calc=None):
    q = {"id": id, "split": split, "answerable": True, "group": group, "question": question,
         "expected_answer": answer, "evidence": evidence}
    if calc:
        q["calc"] = calc
    Q.append(q)


def no(id, split, question, reason, near):
    Q.append({"id": id, "split": split, "answerable": False, "group": "no_evidence", "question": question,
              "expected_behavior": "search_and_abstain", "absence_reason": reason, "near_topic_pages": near})


# ---------------- DEV: 15 answerable + 3 no-evidence ----------------
add("d01", "dev", "table", "How much did IBRD disburse to Latin America and the Caribbean in fiscal 2022?",
    "$8,911 million", [E(103, "table", "TABLE 19, row Latin America and the Caribbean, column FY22", ["8,911"]),
                       E(38, "table", "TABLE 10 (alternative), IBRD disbursements FY22", ["8,911"])])
Q[-1]["evidence_mode"] = "any"
add("d02", "dev", "table", "What were IDA commitments to the Transportation sector in fiscal 2022, and what were they in fiscal 2021?",
    "$5,167 million in FY22 (up from $2,367 million in FY21)",
    [E(107, "table", "TABLE 26, row Transportation, columns FY21 and FY22", ["2,367", "5,167"])])
add("d03", "dev", "table", "What were IBRD's total assets at the end of fiscal 2022?",
    "$317,542 million", [E(105, "table", "TABLE 23, row Total assets, column FY22", ["317,542"])])
add("d04", "dev", "table", "What were IFC's commitments in fiscal 2022 according to the table of World Bank Group commitments?",
    "$22,229 million", [E(17, "table", "TABLE 1, IFC Commitments row, column 2022", ["22,229"])])
add("d05", "dev", "image_diagram", "In the IBRD business model diagram, where does IBRD's income flow?",
    "Income flows to IDA and trust funds",
    [E(105, "diagram", "FIGURE 9: 'Income' bar points to the 'IDA and trust funds' bar (right side)", [], "IDA and trust funds")])
add("d06", "dev", "image_diagram", "On the Commitment to Results map, what result is reported for the Maldives?",
    "Since 2020, automated weather stations increased from 36 to 63",
    [E(113, "map", "Results map, numbered callout 19 (Maldives)", ["36", "63"], "automated weather stations increased from 36 to 63")])
add("d07", "dev", "image_diagram", "In the 2022 summary results globe graphic, what amount is shown for Africa?",
    "$38.5 billion", [E(19, "infographic", "Globe callout 'AFRICA'", ["38.5"])])
add("d08", "dev", "chart", "Which sector received the largest share of IBRD and IDA lending in Eastern and Southern Africa in fiscal 2022, and what was that share?",
    "Public Administration, 18% (of $18.2 billion)", [E(23, "chart", "FIGURE 1 pie chart, slice 'Public Administration'", ["18%", "18.2"])])
add("d09", "dev", "chart", "What share of IBRD and IDA lending in Latin America and the Caribbean in fiscal 2022 went to Health?",
    "18% (of $10.4 billion)", [E(39, "chart", "FIGURE 5 pie chart, slice 'Health'", ["18%", "10.4"])])
add("d10", "dev", "chart", "What share of fiscal 2022 IBRD and IDA lending in Latin America and the Caribbean went to Information and Communications Technologies?",
    "0%", [E(39, "chart", "FIGURE 5 pie chart, slice 'Information and Communications Technologies'", ["0%"])])
# d11 replaced after the first dev run: the original (ESA IBRD + IDA commitments) was answerable
# from a single table (TABLE 2, p22), so it was not a real multi-hop question.
add("d11", "dev", "multi_hop", "What were combined IBRD and IDA commitments to Agriculture, Fishing, and Forestry in fiscal 2022?",
    "$7,619 million (IBRD $3,611 million + IDA $4,008 million)",
    [E(103, "table", "TABLE 20, row Agriculture, Fishing, and Forestry, FY22", ["3,611"]),
     E(107, "table", "TABLE 26, row Agriculture, Fishing, and Forestry, FY22", ["4,008"])],
    "3,611 + 4,008 = 7,619 (US$ millions)")
add("d12", "dev", "multi_hop", "What were combined IBRD and IDA commitments to the Education sector in fiscal 2022?",
    "$3,425 million (IBRD $1,090 million + IDA $2,335 million)",
    [E(103, "table", "TABLE 20, row Education, FY22", ["1,090"]), E(107, "table", "TABLE 26, row Education, FY22", ["2,335"])],
    "1,090 + 2,335 = 3,425 (US$ millions)")
add("d13", "dev", "text", "How much has IBRD raised from private investors since its first bond, and in what year was that first bond issued?",
    "Over $1 trillion since its first bond in 1947",
    [E(76, "text", "paragraph on mobilizing finance", [], "raising over $1 trillion from private investors since its first bond in 1947")])
add("d14", "dev", "text", "How much did IFC commit in trade finance in fiscal 2022, and roughly what share went to IDA and FCV-affected countries?",
    "$9.7 billion (highest ever); nearly 75 percent",
    [E(9, "text", "Message from the President", [], "commitments reached $9.7 billion in trade finance, the highest level ever; nearly 75 percent of this was invested in IDA countries and countries affected by FCV")])
add("d15", "dev", "text", "What gender-equality workplace certification level did the World Bank Group earn in fiscal 2022?",
    "The second level of EDGE certification, EDGE Move",
    [E(88, "text", "staff diversity paragraph", [], "earned the second level of Economic Dividends for Gender Equality (EDGE) certification, EDGE Move")])
no("du1", "dev", "How much did the World Bank commit to Vietnam in fiscal 2022?",
   "Vietnam appears only on p10 (country climate report), p31 (support to the electricity company, no amount) and as a map "
   "label (p113); it is not in the IBRD or IDA top-borrower tables (p104, p108). Checked by search of both text layers and all visual descriptions.",
   [10, 31, 104, 108, 113])
no("du2", "dev", "What was IBRD's equity-to-loans ratio in fiscal 2017?",
   "TABLE 23 covers FY18-FY22 only; 'FY17'/'fiscal 2017' occurs nowhere in the report. Checked by search.", [105])
no("du3", "dev", "How much did Japan pledge to the IDA20 replenishment?",
   "Japan appears only as an Executive Director's country (p13) and as host of the final IDA20 pledging session (p80); "
   "no Japan pledge amount is given. Checked by search for 'Japan'.", [13, 80, 111])

# ---------------- TEST: 24 answerable + 6 no-evidence ----------------
add("t01", "test", "table", "Which country was IBRD's largest borrower in fiscal 2022, and how much were its commitments?",
    "India, $3,986 million", [E(104, "table", "TABLE 22, first row", ["3,986"])])
add("t02", "test", "table", "How much did IDA disburse in Eastern and Southern Africa in fiscal 2022?",
    "$7,133 million", [E(107, "table", "TABLE 25, row Eastern and Southern Africa, column FY22", ["7,133"]),
                       E(22, "table", "TABLE 2 (alternative), IDA disbursements FY22", ["7,133"])])
Q[-1]["evidence_mode"] = "any"
add("t03", "test", "table", "What was the World Bank's (IBRD/IDA) total full-time staff in fiscal 2022, and by how much did it change from fiscal 2020?",
    "12,778 in FY22, up 384 from 12,394 in FY20",
    [E(89, "table", "TABLE 16, row Total full-time staff, FY20 and FY22", ["12,394", "12,778"])], "12,778 - 12,394 = 384")
add("t04", "test", "table", "What was IDA's deployable strategic capital ratio in fiscal 2022, and what was it in fiscal 2021?",
    "26.4% in FY22 (30.4% in FY21)",
    [E(110, "table", "TABLE 29, row Deployable strategic capital ratio (%), FY21 and FY22", ["30.4", "26.4"])])
add("t05", "test", "table", "In the Latin America and the Caribbean regional snapshot, what share of the population had access to electricity in 2000 and in the current data?",
    "91% in 2000 and 98% in the current data",
    [E(40, "table", "TABLE 11, row Access to electricity (% of population), columns 2000 and CURRENT DATA", ["91", "98"])])
add("t06", "test", "table", "What were IBRD commitments to the Health sector in fiscal 2022, and how much higher were they than in fiscal 2021?",
    "$6,252 million in FY22, $3,646 million more than $2,606 million in FY21",
    [E(103, "table", "TABLE 20, row Health, FY21 and FY22", ["2,606", "6,252"])], "6,252 - 2,606 = 3,646")
add("t07", "test", "image_diagram", "In the IDA business model diagram, which activity is financed from Borrowings?",
    "Non-concessional lending",
    [E(109, "diagram", "FIGURE 10: arrow from 'Borrowings' to 'Non-concessional lending'", [], "Non-concessional lending")])
add("t08", "test", "image_diagram", "In the diagram of committees of the Board of Executive Directors, which committee was established in 2003 and what does it consider?",
    "The Ethics Committee; matters relating to the interpretation or application of the Code of Conduct for Board Officials",
    [E(95, "diagram", "FIGURE 8, box 'Ethics Committee'", ["2003"], "Code of Conduct for Board Officials")])
add("t09", "test", "image_diagram", "On the Commitment to Results map, which country is marked by callout 27 and what result is reported?",
    "Yemen: between 2018 and 2022, more than 91,000 households (about a fifth headed by women) received access to affordable solar energy systems",
    [E(113, "map", "Results map, numbered callout 27", ["91,000"],
       "more than 91,000 households, about a fifth of them headed by women, received access to affordable solar energy systems")])
add("t10", "test", "image_diagram", "In the 'Supporting Country Outcomes in Times of Crisis' infographic, how many students benefited from direct learning interventions?",
    "296 million", [E(4, "infographic", "'Rebuilding better' row, graduation-cap icon", ["296"])])
add("t11", "test", "image_diagram", "In the Global Commitments graphic, which region's callout shows $17.4 billion, and what overall total is displayed?",
    "Latin America and the Caribbean; $104.4 billion in total", [E(18, "map", "Globe callout and total box", ["17.4", "104.4"])])
add("t12", "test", "chart", "What share of IBRD and IDA lending in Western and Central Africa in fiscal 2022 went to Transportation, and what was the total lending?",
    "13% of $12.6 billion", [E(27, "chart", "FIGURE 2 pie chart, slice 'Transportation'", ["13%", "12.6"])])
add("t13", "test", "chart", "Which sector had the largest share of IBRD and IDA lending in East Asia and Pacific in fiscal 2022, and what was its share?",
    "Public Administration, 26% (of $7.2 billion)", [E(31, "chart", "FIGURE 3 pie chart, slice 'Public Administration'", ["26%", "7.2"])])
add("t14", "test", "chart", "What share of IBRD and IDA lending in Europe and Central Asia in fiscal 2022 went to Energy and Extractives?",
    "15% (of $8.5 billion)", [E(35, "chart", "FIGURE 4 pie chart, slice 'Energy and Extractives'", ["15%", "8.5"])])
add("t15", "test", "chart", "Which sector received the largest share of IBRD and IDA lending in the Middle East and North Africa in fiscal 2022, and what share was it?",
    "Social Protection, 27% (of $4.9 billion)", [E(43, "chart", "FIGURE 6 pie chart, slice 'Social Protection'", ["27%", "4.9"])])
add("t16", "test", "chart", "In South Asia's fiscal 2022 IBRD and IDA lending by sector, what were the shares of Transportation and of Health?",
    "Transportation 24% and Health 19% (of $9.0 billion)", [E(47, "chart", "FIGURE 7 pie chart, slices 'Transportation' and 'Health'", ["24%", "19%"])])
# t17 and t20 replaced BEFORE any test run (found while analysing dev d11): the originals were
# answerable from one regional table (TABLE 14 p46, TABLE 10 p38), so they were not multi-hop.
add("t17", "test", "multi_hop", "In fiscal 2022, how much more did IDA commit to the Transportation sector than IBRD did?",
    "$2,131 million more (IDA $5,167 million vs IBRD $3,036 million)",
    [E(107, "table", "TABLE 26, row Transportation, FY22", ["5,167"]), E(103, "table", "TABLE 20, row Transportation, FY22", ["3,036"])],
    "5,167 - 3,036 = 2,131 (US$ millions)")
add("t18", "test", "multi_hop", "Which countries were the largest IBRD borrower and the largest IDA borrower in fiscal 2022, and how much larger was the IBRD top borrower's commitment?",
    "India (IBRD, $3,986 million) and Nigeria (IDA, $2,400 million); India's was $1,586 million larger",
    [E(104, "table", "TABLE 22, first row", ["3,986"]), E(108, "table", "TABLE 28, first row", ["2,400"])],
    "3,986 - 2,400 = 1,586 (US$ millions)")
add("t19", "test", "multi_hop", "What was the net (loss) income of IBRD and of IDA in fiscal 2022?",
    "IBRD $3,990 million; IDA $12 million",
    [E(105, "table", "TABLE 23, row Net (loss) income, FY22", ["3,990"]), E(110, "table", "TABLE 29, row Net (loss) income, FY22", ["12"])])
add("t20", "test", "multi_hop", "Which region received the largest IDA commitments in fiscal 2022, and what share of that region's fiscal 2022 IBRD and IDA lending went to Health?",
    "Eastern and Southern Africa ($15,266 million of IDA commitments); Health was 13% of its $18.2 billion lending",
    [E(106, "table", "TABLE 24, FY22 column (largest row: Eastern and Southern Africa)", ["15,266"]),
     E(23, "chart", "FIGURE 1 pie chart, slice 'Health'", ["13%"])])
add("t21", "test", "text", "What is the size of the IDA20 financing envelope, which fiscal years does it cover, and how much do member countries contribute?",
    "$93 billion for fiscal 2023-25, supported by $23.5 billion in contributions from 52 member countries",
    [E(111, "text", "IDA20 replenishment paragraph", [],
       "financing envelope of $93 billion. This envelope, covering fiscal 2023–25, is supported by $23.5 billion in contributions from 52 member countries")])
add("t22", "test", "text", "How much climate finance did the Bank provide to developing countries in fiscal 2022, and how did that compare with fiscal 2019?",
    "$26.2 billion, an 83 percent increase from $14.2 billion in fiscal 2019",
    [E(57, "text", "climate action plan paragraph", [],
       "the Bank provided $26.2 billion of climate finance to developing countries, an 83 percent increase from $14.2 billion in fiscal 2019")])
add("t23", "test", "text", "How much did MIGA issue in guarantees in fiscal 2022?",
    "$4.9 billion", [E(9, "text", "Message from the President", [], "MIGA issued $4.9 billion in guarantees"),
                     E(17, "table", "TABLE 1 (alternative), MIGA Gross issuance, 2022", ["4,935"])])
Q[-1]["evidence_mode"] = "any"
add("t24", "test", "text", "Through June 2022, how many grants had the Health Emergency Preparedness and Response Program awarded, and for what total amount?",
    "34 grants amounting to $117 million",
    [E(56, "text", "Health Emergency Preparedness and Response Program paragraph", [],
       "Through June 2022, the program has awarded 34 grants amounting to $117 million")])
no("tu1", "test", "What is the Gini index of income inequality for Latin America and the Caribbean?",
   "The regional snapshot (TABLE 11, p40) has no inequality indicator; 'Gini' occurs nowhere in the report. Checked by search.", [40])
no("tu2", "test", "How many staff did IFC employ in fiscal 2022?",
   "TABLE 16 (p89) reports IBRD/IDA staff only; no IFC staff count appears anywhere. Checked by search for IFC near 'staff'.", [89])
no("tu3", "test", "How much MIGA guarantee issuance went to Ukraine in fiscal 2022?",
   "MIGA's total ($4.9 billion, p9; TABLE 1 p17) is not broken down by country and MIGA is never mentioned with Ukraine; "
   "Ukraine support on p37 is Bank financing. Checked by search.", [9, 17, 37])
no("tu4", "test", "What were IDA's net commitments in fiscal 2023?",
   "TABLE 29 (p110) and TABLE 24 (p106) end at FY22; fiscal 2023 appears only as the IDA20 period (p8, p106, p109, p111) "
   "without commitment figures. Checked by search.", [106, 110, 111])
no("tu5", "test", "What share of South Asia's IBRD and IDA lending went to Health in fiscal 2021?",
   "FIGURE 7 (p47) shows fiscal 2022 only; sector tables (TABLE 20, 26) are not broken down by region. "
   "Checked by reading p46-47 and p103, p107.", [46, 47, 103, 107])
no("tu6", "test", "What is the under-5 mortality rate in Nigeria?",
   "Under-5 mortality appears only as regional aggregates in the regional snapshot tables (p24, 28, 32, 36, 40, 44, 48); "
   "no country-level value for Nigeria. Checked by search.", [26, 28])

out = ROOT / "advanced/benchmark/questions.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(Q, ensure_ascii=False, indent=1), encoding="utf-8")
print(Counter((q["split"], q["group"]) for q in Q))
