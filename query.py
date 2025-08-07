import xml.etree.ElementTree as ET
import os
import sys

def load_xml(xml_file):
    """Load XML file and return root element."""
    if not os.path.exists(xml_file):
        print(f"ERROR: XML file '{xml_file}' not found!")
        return None
    try:
        tree = ET.parse(xml_file)
        return tree.getroot()
    except ET.ParseError as e:
        print(f"ERROR: Failed to parse XML file: {e}")
        return None

def find_calibrator_by_name(root, iau_name):
    """Find and return calibrator element matching given J2000 IAU_NAME."""
    if root is None:
        return None
        
    for calib in root.findall('calibrator'):
        j2000 = calib.find('header/j2000')
        if j2000 is not None:
            name = j2000.findtext('IAU_NAME', '').strip()
            if name == iau_name:
                return calib
    return None

def list_calibrators_by_band(root, band_name):
    """Return list of calibrators having the specified band."""
    if root is None:
        return []
        
    found = []
    for calib in root.findall('calibrator'):
        bands = calib.findall('bands/band')
        for band in bands:
            if band.findtext('BAND', '').strip() == band_name:
                found.append(calib)
                break
    return found

def print_calibrator(calib):
    """Print readable info about a calibrator element."""
    if calib is None:
        print("No calibrator data to display.")
        return
        
    j2000 = calib.find('header/j2000')
    b1950 = calib.find('header/b1950')
    
    if j2000 is None:
        print("ERROR: Missing J2000 data for calibrator")
        return
    
    print(f"Calibrator: {j2000.findtext('IAU_NAME', 'N/A')} (J2000)")
    print(f"  RA: {j2000.findtext('RA', '')}")
    print(f"  DEC: {j2000.findtext('DEC', '')}")
    print(f"  Position Code: {j2000.findtext('PC', '')}")
    print(f"  Position Reference: {j2000.findtext('POS_REF', '')}")
    print(f"  Alt Name: {j2000.findtext('ALT_NAME', '')}")
    
    if b1950 is not None and b1950.findtext('IAU_NAME'):
        print(f"B1950 Name: {b1950.findtext('IAU_NAME')}")
        print(f"  RA: {b1950.findtext('RA')}")
        print(f"  DEC: {b1950.findtext('DEC')}")
    
    print("Bands:")
    bands_found = calib.findall('bands/band')
    if not bands_found:
        print("  No band data available")
    else:
        for band in bands_found:
            band_name = band.findtext('BAND', '')
            band_code = band.findtext('BAND_CODE', '')
            a_code = band.findtext('A_CODE', '')
            b_code = band.findtext('B_CODE', '')
            c_code = band.findtext('C_CODE', '')
            d_code = band.findtext('D_CODE', '')
            flux = band.findtext('FLUX_JY', '')
            uvmin = band.findtext('UVMIN_KLAMBDA', '')
            uvmax = band.findtext('UVMAX_KLAMBDA', '')
            
            print(f"  {band_name} [{band_code}]: "
                  f"A={a_code} B={b_code} C={c_code} D={d_code} "
                  f"Flux={flux} Jy "
                  f"UVMIN={uvmin} UVMAX={uvmax}")
    
    print("-" * 60)

def interactive_query(xml_file):
    """Main interactive query function."""
    print(f"Loading XML file: {xml_file}")
    root = load_xml(xml_file)
    
    if root is None:
        print("Failed to load XML file. Exiting.")
        return
    
    calibrator_count = len(root.findall('calibrator'))
    print(f"Loaded XML with {calibrator_count} calibrators.")
    
    if calibrator_count == 0:
        print("No calibrators found in XML file.")
        return
    
    while True:
        print("\nChoose an option:")
        print("1. Find calibrator by J2000 IAU_NAME")
        print("2. List calibrators with a specified band")
        print("3. Show first 5 calibrators")
        print("4. Exit")
        
        try:
            choice = input("Enter choice (1-4): ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            break
            
        if choice == '1':
            try:
                name = input("Enter exact J2000 IAU_NAME (e.g., 0005+383): ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nOperation cancelled.")
                continue
                
            if not name:
                print("Please enter a valid calibrator name.")
                continue
                
            calib = find_calibrator_by_name(root, name)
            if calib:
                print_calibrator(calib)
            else:
                print(f"Calibrator '{name}' not found.")
                # Show some similar names
                similar = []
                for c in root.findall('calibrator'):
                    j2000 = c.find('header/j2000')
                    if j2000 is not None:
                        cname = j2000.findtext('IAU_NAME', '').strip()
                        if name.lower() in cname.lower() or cname.lower() in name.lower():
                            similar.append(cname)
                
                if similar:
                    print(f"Similar names found: {', '.join(similar[:5])}")
                    
        elif choice == '2':
            try:
                band = input("Enter band name (e.g., 20cm, 6cm): ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nOperation cancelled.")
                continue
                
            if not band:
                print("Please enter a valid band name.")
                continue
                
            calib_list = list_calibrators_by_band(root, band)
            print(f"Found {len(calib_list)} calibrators with band '{band}'. Showing first 10:")
            
            for i, cal in enumerate(calib_list[:10]):
                j2000 = cal.find('header/j2000')
                if j2000 is not None:
                    jname = j2000.findtext('IAU_NAME', 'Unknown')
                    print(f"  {i+1}. {jname}")
                    
        elif choice == '3':
            print("First 5 calibrators in the database:")
            for i, cal in enumerate(root.findall('calibrator')[:5]):
                j2000 = cal.find('header/j2000')
                if j2000 is not None:
                    jname = j2000.findtext('IAU_NAME', 'Unknown')
                    bands = len(cal.findall('bands/band'))
                    print(f"  {i+1}. {jname} ({bands} bands)")
                    
        elif choice == '4':
            print("Exiting.")
            break
            
        else:
            print("Invalid choice. Please enter 1, 2, 3, or 4.")

def main():
    """Main function with command line argument support."""
    if len(sys.argv) > 1:
        xml_file = sys.argv[1]
    else:
        # Try common XML file names
        possible_files = [
            "vla_calibrators_from_web_fixed.xml",
            "vla_calibrators_from_web.xml", 
            "calibrators.xml"
        ]
        
        xml_file = None
        for filename in possible_files:
            if os.path.exists(filename):
                xml_file = filename
                break
        
        if xml_file is None:
            print("No XML file found. Please specify one:")
            print("Usage: python xml_query.py <xml_file>")
            print(f"Looked for: {', '.join(possible_files)}")
            return
    
    interactive_query(xml_file)

if __name__ == "__main__":
    main()
