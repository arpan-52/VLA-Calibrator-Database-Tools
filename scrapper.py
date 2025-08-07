import requests
from bs4 import BeautifulSoup, NavigableString
import re
import xml.etree.ElementTree as ET

def create_text_element(parent, tag, text):
    el = ET.SubElement(parent, tag)
    el.text = text if text is not None else ""
    return el

def indent(elem, level=0):
    i = "\n" + level * "  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        for e in elem:
            indent(e, level+1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i

def clean_line(s):
    """ Clean markdown links, parentheses, stray URLs from a str line. """
    s = re.sub(r"\[([^\]]*)\]\([^\)]*\)", r"\1", s)
    s = re.sub(r"\([^\s)]+://[^\s)]+\)", '', s)  # Remove URLs in ()
    s = re.sub(r"http[s]?://\S+", "", s)
    return s.strip()

def parse_band_line_fixed(line):
    """
    Parse a band line using fixed-width column approach.
    Expected format based on VLA documentation:
    BAND    CODE A B C D    FLUX(Jy)    UVMIN(kL)  UVMAX(kL)
     90cm    P  S S S X          7            1
     20cm    L  X P P P       2.40                  50
    """
    # Remove any trailing comments like "visplot"
    line = re.sub(r'\s+visplot\s*$', '', line)
    
    # Define approximate column positions based on the header format
    # These positions are based on the typical VLA calibrator format
    try:
        # Extract band (first 8 characters, right-padded)
        band = line[0:8].strip()
        
        # Extract band code (next 4 characters)
        band_code = line[8:12].strip()
        
        # Extract A, B, C, D codes (each roughly 2 characters)
        a_code = line[12:14].strip()
        b_code = line[14:16].strip() 
        c_code = line[16:18].strip()
        d_code = line[18:20].strip()
        
        # The rest of the line contains flux and UV ranges
        remainder = line[20:].strip()
        
        # Split remainder by whitespace to get numeric values
        parts = remainder.split()
        
        # First number should be flux
        flux = parts[0] if len(parts) > 0 and parts[0].replace('.', '').isdigit() else ""
        
        # For UV ranges, we need to look at the original line positioning
        # Find where numbers appear after the flux value
        uvmin = ""
        uvmax = ""
        
        if len(parts) > 1:
            # Look at the actual character positions in the original line
            # to determine if numbers are in UVMIN or UVMAX columns
            
            for i, part in enumerate(parts[1:], 1):  # Skip flux (parts[0])
                if part.replace('.', '').isdigit():
                    # Find the position of this number in the original line
                    num_pos = line.find(part, 20)  # Start search after column 20
                    
                    # Based on typical VLA format:
                    # UVMIN column is around position 40-50
                    # UVMAX column is around position 55-65
                    if 35 <= num_pos <= 50:
                        uvmin = part
                    elif num_pos > 50:
                        uvmax = part
                    elif not uvmin:  # If no clear positioning, assume first number is UVMIN
                        uvmin = part
                    elif not uvmax:  # Second number is UVMAX
                        uvmax = part
        
        return {
            "BAND": band,
            "BAND_CODE": band_code,
            "A_CODE": a_code,
            "B_CODE": b_code,
            "C_CODE": c_code,
            "D_CODE": d_code,
            "FLUX_JY": flux,
            "UVMIN_KLAMBDA": uvmin,
            "UVMAX_KLAMBDA": uvmax,
        }
        
    except Exception as e:
        print(f"Error parsing band line '{line}': {e}")
        return None

def parse_cal_block(block_lines):
    bands = []
    header, b1950 = {}, {}
    
    # Regex patterns for header parsing
    jheader_pat = re.compile(
        r"^(?:\[(?P<iauname>\S+)\]\([^\)]+\)|(?P<iauname2>\S+))\s+J2000\s+(?P<pc>\w)\s+(?P<ra>\S+)\s+(?P<dec>\S+)\s*(?P<posref>[A-Za-z0-9]+)?\s*(?P<altname>[A-Za-z0-9.]+)?"
    )
    bheader_pat = re.compile(
        r"^(?:\[(?P<iauname>\S+)\]|(?P<iauname2>\S+))\s+B1950\s+(?P<pc>\w)\s+(?P<ra>\S+)\s+(?P<dec>\S+)"
    )
    
    # Simple pattern to identify band lines - just look for the band format
    band_line_pat = re.compile(r'^\s*([0-9.]+(?:cm|mm))\s+([A-Z])\s+')

    lines = [clean_line(l) for l in block_lines if l.strip() and 
             not l.strip().startswith('-') and 
             not l.strip().startswith('=') and 
             not l.strip().startswith('BAND')]

    print(f"Processing calibrator block with {len(lines)} lines")
    
    for i, s in enumerate(lines):
        print(f"  Line {i}: '{s}'")
        
        # Try J2000 header
        m = jheader_pat.match(s)
        if m:
            iau = m.group('iauname') or m.group('iauname2')
            header = {
                "IAU_NAME": iau,
                "EQUINOX": "J2000",
                "PC": m.group('pc') or "",
                "RA": m.group('ra') or "",
                "DEC": m.group('dec') or "",
                "POS_REF": m.group('posref') or "",
                "ALT_NAME": m.group('altname') or "",
            }
            print(f"    Found J2000 header: {iau}")
            continue
            
        # Try B1950 header
        m = bheader_pat.match(s)
        if m:
            iau = m.group('iauname') or m.group('iauname2')
            b1950 = {
                "IAU_NAME": iau,
                "EQUINOX": "B1950",
                "PC": m.group('pc') or "",
                "RA": m.group('ra') or "",
                "DEC": m.group('dec') or "",
            }
            print(f"    Found B1950 header: {iau}")
            continue
            
        # Try band data using the new fixed-width approach
        if band_line_pat.match(s):
            band_data = parse_band_line_fixed(s)
            if band_data:
                bands.append(band_data)
                print(f"    Added band: {band_data['BAND']} with UVMIN={band_data['UVMIN_KLAMBDA']}, UVMAX={band_data['UVMAX_KLAMBDA']}")

    # Create XML structure
    root = ET.Element("calibrator")
    header_el = ET.SubElement(root, "header")
    jheader_el = ET.SubElement(header_el, "j2000")
    for tag in ["IAU_NAME","EQUINOX","PC","RA","DEC","POS_REF","ALT_NAME"]:
        create_text_element(jheader_el, tag, header.get(tag, ""))
    bheader_el = ET.SubElement(header_el, "b1950")
    for tag in ["IAU_NAME","EQUINOX","PC","RA","DEC"]:
        create_text_element(bheader_el, tag, b1950.get(tag,""))
    bands_el = ET.SubElement(root, "bands")
    for band in bands:
        band_el = ET.SubElement(bands_el, "band")
        for k in ["BAND","BAND_CODE","A_CODE", "B_CODE", "C_CODE", "D_CODE", "FLUX_JY", "UVMIN_KLAMBDA","UVMAX_KLAMBDA"]:
            create_text_element(band_el, k, band.get(k,""))
    
    print(f"Created XML for calibrator: {header.get('IAU_NAME', 'Unknown')} with {len(bands)} bands")
    return root

def scrape_and_export_xml(url, xml_file="vla_calibrators_from_web_fixed.xml"):
    print(f"Scraping VLA calibrator list from: {url}")
    resp = requests.get(url)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, 'html.parser')

    results = []
    in_block = False
    block_lines = []
    calibrator_count = 0
    
    # Search every <pre> tag (calibrators are in preformatted blocks)
    for pre in soup.find_all('pre'):
        lines = pre.get_text().splitlines()
        for idx, line in enumerate(lines):
            # Every block starts with calibrator J2000 entry
            if "J2000" in line:
                in_block = True
                block_lines = [line]
                continue
            if in_block:
                block_lines.append(line)
                # Each block ends with a blank line or EOF
                if idx+1 == len(lines) or not lines[idx+1].strip():
                    print(f"\n=== Processing calibrator {calibrator_count + 1} ===")
                    try:
                        xmlnode = parse_cal_block(block_lines)
                        results.append(xmlnode)
                        calibrator_count += 1
                    except Exception as e:
                        print(f"Error processing calibrator block: {e}")
                        print(f"Block lines were: {block_lines}")
                    in_block = False

    # Create final XML
    root = ET.Element("calibrators")
    for node in results:
        root.append(node)
    indent(root)
    tree = ET.ElementTree(root)
    tree.write(xml_file, encoding="utf-8", xml_declaration=True)
    print(f"\nExtracted {len(results)} calibrators. XML saved as {xml_file}")
    
    # Print a summary of the first few calibrators
    print("\n=== SUMMARY ===")
    for i, result in enumerate(results[:5]):
        name = result.find('.//IAU_NAME')
        name_text = name.text if name is not None else "Unknown"
        bands = result.findall('.//band')
        print(f"{i+1}. {name_text}: {len(bands)} bands")
        for band in bands[:3]:  # Show first 3 bands
            band_name = band.find('BAND').text if band.find('BAND') is not None else ""
            uvmin = band.find('UVMIN_KLAMBDA').text if band.find('UVMIN_KLAMBDA') is not None else ""
            uvmax = band.find('UVMAX_KLAMBDA').text if band.find('UVMAX_KLAMBDA') is not None else ""
            print(f"   {band_name}: UVMIN={uvmin}, UVMAX={uvmax}")

if __name__ == "__main__":
    scrape_and_export_xml("https://science.nrao.edu/facilities/vla/observing/callist")
