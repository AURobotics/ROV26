import zlib

def calculate_crc32(data):
    # Convert string to bytes
    if isinstance(data, str):
        data = data.encode('utf-8')
    
    # zlib.crc32 starts with 0 by default
    crc = zlib.crc32(data, 0xFFFFFFFF)
    
    # Apply final XOR with 0xFFFFFFFF (~)
    return crc ^ 0xFFFFFFFF

def compare_crc32(data, expected_crc):
    calculated = calculate_crc32(data)
    
    # Handle hex string input
    if isinstance(expected_crc, str):
        expected_crc = int(expected_crc, 16)
    
    matches = calculated == expected_crc
    
    if not matches:
        print(f"CRC mismatch!")
        print(f"  Calculated: 0x{calculated:08X} ({calculated})")
        print(f"  Expected:   0x{expected_crc:08X} ({expected_crc})")
    else:
        print(f"CRC matches: 0x{calculated:08X}")
    
    return matches
