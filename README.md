# VLA Calibrator Database Tools

Simple Python scripts to convert NRAO's web-based VLA calibrator list into XML format for easier programmatic access.

---

## Background

The NRAO's VLA calibrator database is available as web tables, which are not ideal for automated workflows. These tools scrape the data and convert it into structured XML, making it easier to integrate into pipelines and search programs.

---

## What It Does

- **Web scraping**: Downloads calibrator data from the NRAO website  
- **XML conversion**: Converts web tables into structured XML  
- **Query tool**: CLI interface to search the XML database  
- **Pipeline friendly**: XML format is compatible with CASA, AIPS, etc.

---

## Files

- `scrapper.py` – Downloads and converts calibrator data to XML  
- `query.py` – CLI tool to query the XML database  
- `vla_calibrators_from_web_fixed.xml` – The generated XML file  

---

## Installation

Install required Python packages:

```bash
pip install requests beautifulsoup4 lxml
```
## Usage
Generate the XML database

python scrapper.py

This downloads the calibrator list from the NRAO and saves it as an XML file.
Query the XML database

python query.py

Simple menu interface to look up calibrators by name or frequency band.
## Data Structure
``` bash
Each calibrator entry contains:
Positional Information

    J2000 coordinates (RA, DEC, position codes)

    B1950 coordinates (when available)

    Position references and alternative names

Observational Data

    Frequency bands with measured flux densities

    VLA configuration suitability (A, B, C, D arrays)

    UV coverage ranges in kilolambda (kλ)
```
 ## Example Output
```bash
Calibrator: 3C147 (J2000)
  RA: 05:42:36.138
  DEC: +49:51:07.23
  Position Code: P
Bands:
  20cm [L]: A=P B=P C=P D=P Flux=22.46 Jy UVMIN=0.1 UVMAX=500
  6cm [C]: A=P B=P C=S D=S Flux=12.34 Jy UVMIN=0.3 UVMAX=750
```
## XML Schema Example
```bash
<calibrators>
  <calibrator>
    <header>
      <j2000>
        <IAU_NAME>3C147</IAU_NAME>
        <RA>05:42:36.138</RA>
        <DEC>+49:51:07.23</DEC>
      </j2000>
    </header>
    <bands>
      <band>
        <BAND>20cm</BAND>
        <FLUX_JY>22.46</FLUX_JY>
        <A_CODE>P</A_CODE>
      </band>
    </bands>
  </calibrator>
</calibrators>
```
## Configuration Codes
```bash
Code	Meaning	Usage
P	Primary	Recommended calibrator
S	Secondary	Acceptable alternative
X	Excluded	Avoid for this config
Array Configurations
Array	Baseline	Resolution (@20cm)
A	36 km	~0.04″
B	11 km	~0.13″
C	3.4 km	~0.4″
D	1 km	~1.3″
```
## Applications
Pipeline Integration

    CASA calibrator selection tools

    Custom Python data pipelines

    Observational planning tools

## Typical Python Workflow
```bash
import xml.etree.ElementTree as ET
tree = ET.parse('vla_calibrators_from_web_fixed.xml')
root = tree.getroot()

# Find 20cm calibrators suitable for C-array
for calib in root.findall('calibrator'):
    for band in calib.findall('.//band'):
        if band.findtext('BAND') == '20cm' and band.findtext('C_CODE') == 'P':
            name = calib.findtext('.//IAU_NAME')
            flux = band.findtext('FLUX_JY')
            print(f"{name}: {flux} Jy")
```
