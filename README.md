# CE3204
CE3204 Data Management for Civil Engineers Project 
Steel Frame Analysis & Optimization Tool

---

## 🌐 Live App
https://steelframeanalysis.streamlit.app

---

## 💻 How to Run Locally

### Step 1 — Download the Project
Download or clone the entire repository from GitHub.

---

### Step 2 — Open in VS Code
Open the project folder in Visual Studio Code.

Make sure Python is installed.

---

### Step 3 — Install Dependencies
Open the terminal in VS Code and run:

pip install -r requirements.txt

---

### Step 4 — Run the App
In the terminal, run:

streamlit run app.py

---

### Step 5 — Open in Browser
If it does not open automatically, go to:

http://localhost:8501

---

## ⚠️ Important Notes
- Do not change the folder structure  
- Ensure the following are in the root directory:
  - app.py  
  - requirements.txt  
  - steel_frame/  
  - data/  

---

## 🚀 Usage Tips
- Use “Load Sample Input” to test quickly  
- Use bulk input tools to save time when entering storey data  
- If Module 2 shows “No feasible solution”, try:
  - relaxing constraints  
  - reducing grouping  
  - allowing more section options  

---

## 📊 Visualization Guide
Utilization ratio (U) color coding:

- Yellow → U < 0.4 (overdesigned)  
- Green → 0.4 ≤ U < 0.8  
- Light Green → 0.8 ≤ U ≤ 1.0  
- Red → U > 1.0 (failing)  

---

## 🧠 Key Idea
- U < 1.0 → Safe  
- U > 1.0 → Fails  
