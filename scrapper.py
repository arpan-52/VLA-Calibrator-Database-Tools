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
    """Clean markdown links, parentheses, stray URLs from a str line."""
    s = re.sub(r"\[([^\]]*)\]\([^\)]*\)", r"\1", s)
    s = re.sub(r"\([^\s)]+://[^\s)]+\)", '', s)  # Remove URLs in ()
    s = re.sub(r"http[s]?://\S+", "", s)
    return s.strip()

def parse_band_line_robust(line):
    """
    Robust parser for VLA band lines using position-based UV parsing.
    
    Uses actual column positions from header to correctly assign UVMIN/UVMAX values.
    UVMIN starts at position 35, UVMAX starts at position 46.
    """
    # Remove any trailing comments like "visplot"
    original_line = line
    line_clean = re.sub(r'\s+visplot\s*$', '', line).strip()
    
    print(f"    Parsing band line: '{line_clean}'")
    
    try:
        # Split the line into parts for basic parsing
        parts = line_clean.split()
        if len(parts) < 7:
            print(f"    Not enough parts: {len(parts)}")
            return None
            
        print(f"    Split parts: {parts}")
        
        # Extract basic fields using split method
        band = parts[0]
        
        # Find flux position
        flux_idx = -1
        for i, part in enumerate(parts):
            if re.match(r'^\d*\.?\d+$', part) and float(part) > 0.05:
                flux_idx = i
                break
        
        if flux_idx == -1:
            print(f"    Could not find flux value")
            return None
            
        flux = parts[flux_idx]
        
        # Extract codes (everything between band and flux)
        codes = parts[1:flux_idx]
        if len(codes) < 5:
            print(f"    Not enough codes: {len(codes)}")
            return None
            
        band_code = codes[0]
        a_code = codes[1]
        b_code = codes[2] 
        c_code = codes[3]
        d_code = codes[4]
        
        print(f"    Band: {band}, Code: {band_code}, Antenna codes: [{a_code},{b_code},{c_code},{d_code}], Flux: {flux}")
        
        # Position-based UV parsing using header-derived column positions
        uvmin_col_pos = 35  # UVMIN column starts at position 35
        uvmax_col_pos = 46  # UVMAX column starts at position 46
        
        uvmin = ""
        uvmax = ""
        
        # Find all numeric values after the flux in the original line
        uv_candidates = []
        for i in range(flux_idx + 1, len(parts)):
            if re.match(r'^\d*\.?\d+$', parts[i]):
                # Find the position of this number in the original line
                search_start = original_line.find(flux) + len(flux)
                pos = original_line.find(parts[i], search_start)
                uv_candidates.append((parts[i], pos))
                print(f"      UV candidate: '{parts[i]}' at position {pos}")
        
        # Assign UV values based on column positions
        # Check UVMAX first since it comes after UVMIN
        for uv_value, pos in uv_candidates:
            if pos >= uvmax_col_pos:  # Check UVMAX first
                if not uvmax:
                    uvmax = uv_value
                    print(f"      Assigned UVMAX: '{uv_value}' (pos {pos} >= {uvmax_col_pos})")
            elif pos >= uvmin_col_pos:  # Then check UVMIN
                if not uvmin:
                    uvmin = uv_value  
                    print(f"      Assigned UVMIN: '{uv_value}' (pos {pos} >= {uvmin_col_pos})")
            else:
                print(f"      UV value '{uv_value}' at pos {pos} is before columns - ignoring")
        
        # Fallback logic
        if not uvmin and not uvmax and uv_candidates:
            # Single value - assign to UVMAX based on analysis
            uvmax = uv_candidates[0][0]
            print(f"      FALLBACK: Single UV '{uvmax}' assigned to UVMAX")
        
        result = {
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
        
        print(f"    Final result: UVMIN='{uvmin}', UVMAX='{uvmax}'")
        return result
        
    except Exception as e:
        print(f"Error parsing band line '{original_line}': {e}")
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
    
    # Pattern to identify band lines - look for band format at start of line
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
            
        # Try band data - use robust parsing
        if band_line_pat.match(s):
            band_data = parse_band_line_robust(s)
                
            if band_data:
                bands.append(band_data)
                print(f"    Added band: {band_data['BAND']} code={band_data['BAND_CODE']} with antenna codes [{band_data['A_CODE']},{band_data['B_CODE']},{band_data['C_CODE']},{band_data['D_CODE']}], UVMIN={band_data['UVMIN_KLAMBDA']}, UVMAX={band_data['UVMAX_KLAMBDA']}")

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
            a_code = band.find('A_CODE').text if band.find('A_CODE') is not None else ""
            b_code = band.find('B_CODE').text if band.find('B_CODE') is not None else ""
            c_code = band.find('C_CODE').text if band.find('C_CODE') is not None else ""
            d_code = band.find('D_CODE').text if band.find('D_CODE') is not None else ""
            uvmin = band.find('UVMIN_KLAMBDA').text if band.find('UVMIN_KLAMBDA') is not None else ""
            uvmax = band.find('UVMAX_KLAMBDA').text if band.find('UVMAX_KLAMBDA') is not None else ""
            print(f"   {band_name}: Codes=[{a_code},{b_code},{c_code},{d_code}] UVMIN={uvmin}, UVMAX={uvmax}")

if __name__ == "__main__":
    scrape_and_export_xml("https://science.nrao.edu/facilities/vla/observing/callist")
