from typing import List, Dict, Optional
import random
import io
import re

class DepositoryService:
    # Seed data mapped to common demo Demat IDs (16 digits)
    # CDSL IDs typically start with 120, 130 etc.
    DEP_SEED_DATA = {
        "1208160012345678": [
            {"symbol": "RELIANCE.BSE", "quantity": 25, "avg_cost": 2450.0},
            {"symbol": "HDFCBANK.BSE", "quantity": 100, "avg_cost": 1550.0},
            {"symbol": "TCS.BSE", "quantity": 15, "avg_cost": 3300.0}
        ],
        "1301240087654321": [
            {"symbol": "INFY.BSE", "quantity": 200, "avg_cost": 1420.0},
            {"symbol": "WIPRO.BSE", "quantity": 500, "avg_cost": 410.0}
        ],
        "default": [
            {"symbol": "RELIANCE.BSE", "quantity": 10, "avg_cost": 2350.50},
            {"symbol": "HDFCBANK.BSE", "quantity": 40, "avg_cost": 1620.0},
            {"symbol": "TCS.BSE", "quantity": 5, "avg_cost": 3100.0},
            {"symbol": "NIFTYBEES.BSE", "quantity": 500, "avg_cost": 205.75},
            {"symbol": "INFY.BSE", "quantity": 25, "avg_cost": 1450.0}
        ]
    }

    @classmethod
    async def decrypt_pdf(cls, file_bytes: bytes, password: Optional[str] = None) -> str:
        """
        Decrypts a password-protected PDF and extracts text content.
        Uses pikepdf for decryption and pymupdf (fitz) for text extraction.
        """
        try:
            import pikepdf
            import fitz  # PyMuPDF
            
            print(f"[DepositoryService] Decrypting PDF, size: {len(file_bytes)} bytes")
            
            # Try to open with pikepdf (handles encryption)
            pdf_stream = io.BytesIO(file_bytes)
            
            try:
                # First try without password
                print(f"[DepositoryService] Attempting to open PDF without password...")
                pdf = pikepdf.open(pdf_stream)
                print(f"[DepositoryService] PDF opened without password")
            except pikepdf.PasswordError:
                # PDF is encrypted, need password
                print(f"[DepositoryService] PDF is encrypted")
                if not password:
                    raise ValueError("PDF is password protected. Please provide the password (usually your PAN number, e.g., ABCDE1234F)")
                
                print(f"[DepositoryService] Attempting to open PDF with provided password: {password}")
                pdf_stream.seek(0)
                try:
                    pdf = pikepdf.open(pdf_stream, password=password)
                    print(f"[DepositoryService] PDF decrypted successfully")
                except pikepdf.PasswordError:
                    print(f"[DepositoryService] Incorrect password")
                    raise ValueError("Incorrect password. CAS password is usually your PAN number (e.g., ABCDE1234F)")
            except Exception as e:
                print(f"[DepositoryService] Error opening with pikepdf: {e}")
                raise ValueError(f"Invalid PDF file: {str(e)}")
            
            # Save decrypted PDF to memory
            decrypted_stream = io.BytesIO()
            pdf.save(decrypted_stream)
            pdf.close()
            decrypted_stream.seek(0)
            
            # Extract text using PyMuPDF (fitz)
            print(f"[DepositoryService] Extracting text with PyMuPDF...")
            try:
                doc = fitz.open(stream=decrypted_stream.read(), filetype="pdf")
                text = ""
                for i, page in enumerate(doc):
                    page_text = page.get_text()
                    text += page_text
                    print(f"[DepositoryService] Page {i+1} text length: {len(page_text)}")
                doc.close()
                print(f"[DepositoryService] Total extracted text length: {len(text)}")
                return text
            except Exception as e:
                print(f"[DepositoryService] Error extraction text: {e}")
                raise ValueError(f"Error extracting text from PDF: {str(e)}")
            
        except ImportError as e:
            print(f"[DepositoryService] Missing libraries: {e}")
            raise ValueError(f"PDF processing libraries not installed: {e}")
        except ValueError:
            raise
        except Exception as e:
            print(f"[DepositoryService] Unexpected error: {e}")
            raise ValueError(f"Error processing PDF: {str(e)}")

    @classmethod
    async def parse_cas_statement(cls, content: str, file_bytes: Optional[bytes] = None, password: Optional[str] = None) -> List[Dict]:
        """
        Parses content from a CAS file (PDF or text).
        For PDFs, decrypts if necessary and extracts text.
        Then parses for stock holdings in various formats.
        """
        text_content = content
        
        # If we have file bytes, try to process as PDF
        if file_bytes and len(file_bytes) > 4:
            print(f"[DepositoryService] Parser Code Version: FIXED_PDF_BLOCK_V3")
            
            # Check if it's a PDF (starts with %PDF or has %PDF within first 1024 bytes)
            is_pdf = file_bytes[:4] == b'%PDF' or b'%PDF' in file_bytes[:1024]
            print(f"[DepositoryService] File bytes length: {len(file_bytes)}, Is PDF: {is_pdf}")
            
            if is_pdf:
                print(f"[DepositoryService] Attempting PDF decryption...")
                text_content = await cls.decrypt_pdf(file_bytes, password)
                print(f"[DepositoryService] Extracted text length: {len(text_content)}")

        lines = [line.strip() for line in text_content.split('\n') if line.strip()]
        
        # Write to temp directory for debugging (won't trigger reload)
        try:
            import tempfile
            import os
            temp_path = os.path.join(tempfile.gettempdir(), "cas_debug.txt")
            with open(temp_path, "w", encoding="utf-8") as f:
                f.write(text_content)
        except Exception as e:
            print(f"Failed to write log: {e}")

        print(f"[DepositoryService] DEBUG: Extracted Text (First 1000 chars):\n{text_content[:1000]}")
        
        parsed_holdings = []
        current_holding = {}
        
        for i, line in enumerate(lines):
            # Check for ISIN (Key for new block)
            # Fits format: INE... or INF... (12 chars alphanumeric)
            # Relaxed regex to find ISIN anywhere in the line
            isin_match = re.search(r'([A-Z]{3}[A-Z0-9]{9})', line)
            
            if isin_match:
                # If we were processing a previous holding, save it if it has qty
                if current_holding.get("isin") and current_holding.get("quantity"):
                    try:
                        cls._add_holding(parsed_holdings, current_holding["isin"], current_holding["quantity"], current_holding.get("avg_cost", 0))
                    except Exception as e:
                        print(f"[DepositoryService] Error adding holding: {e}")
                
                # Start new holding
                current_holding = {"isin": isin_match.group(1)}
                
                # Check if Quantity/Price are on the SAME line (Tabular format)
                # Text after ISIN in the line
                remaining_text = line[isin_match.end():]
                # Find all numbers (int or float) in the rest of the line
                # e.g. " 99 2692 2586 256014" -> ['99', '2692', ...]
                numbers = re.findall(r'[\s:]+([\d,]+(?:\.\d+)?)', remaining_text)
                
                if numbers:
                    # Clean commas
                    clean_nums = [n.replace(',', '') for n in numbers]
                    try:
                        # First number is Quantity
                        current_holding["quantity"] = int(float(clean_nums[0]))
                        
                        # Second number is likely Avg Cost (or Price)
                        if len(clean_nums) > 1:
                            current_holding["avg_cost"] = float(clean_nums[1])
                            
                        # If there's a 4th number (Market Value), we might ignore it or use it to verify
                        # For now, ISIN + Qty + Avg is enough
                    except (ValueError, IndexError):
                        pass
                
                continue
            
            # If inside a holding block, look for details (Multi-line format)
            if current_holding.get("isin"):
                # Look for Quantity: Any number on its own line or loosely formatted
                # Accepts 99, 99.00, 155.000 etc.
                # Regex: Start of line, number, optional suffix
                qty_match = re.match(r'^([\d,]+(?:\.\d+)?)$', line.strip())
                
                if qty_match and not current_holding.get("quantity"):
                    try:
                        qty_str = qty_match.group(1).replace(',', '')
                        current_holding["quantity"] = int(float(qty_str))
                    except ValueError:
                        pass
                    continue
                
                # Look for Value/Price context
                # If we verify a line looks like a value (has commas, 2 decimals): 26,884.75
                val_match = re.match(r'^([\d,]+)\.(\d{2})$', line.strip())
                if val_match:
                    try:
                        val_str = f"{val_match.group(1)}.{val_match.group(2)}".replace(',', '')
                        value = float(val_str)
                        # If we have qty, checking if this is total value or unit price
                        qty = current_holding.get("quantity", 0)
                        if qty > 0:
                            # Heuristic: If value is closer to existing avg_cost * qty, it's Total Value
                            # Otherwise might be Unit Price
                            current_holding["avg_cost"] = value / qty # Derived avg cost
                    except ValueError:
                        pass

        # Save the last holding
        if current_holding.get("isin") and current_holding.get("quantity"):
            try:
                cls._add_holding(parsed_holdings, current_holding["isin"], current_holding["quantity"], current_holding.get("avg_cost", 0))
            except Exception as e:
                print(f"[DepositoryService] Error adding last holding: {e}")
        
        print(f"[DepositoryService] DEBUG: Returning {len(parsed_holdings)} holdings")
        return parsed_holdings

    @classmethod
    def _add_holding(cls, holdings: List[Dict], isin: str, quantity: int, avg_cost: float):
        # ISIN to symbol mapping (common Indian stocks + Log Analysis)
        isin_map = {
            # Large Cap
            "INE002A01018": "RELIANCE.BSE",
            "INE467B01029": "TCS.BSE",
            "INE040A01034": "HDFCBANK.BSE",
            "INE009A01021": "INFY.BSE",
            "INE090A01021": "ICICIBANK.BSE",
            "INE245A01021": "SBIN.BSE",
            "INE154A01025": "ITC.BSE",
            "INE002B01016": "TATAPOWER.BSE",
            "INE238A01034": "AXISBANK.BSE",
            "INE018A01030": "LT.BSE",
            
            # Mid/Small Cap (From User Logs)
            "INE528G01035": "YESBANK.BSE",
            "INE752E01010": "PVRINOX.BSE",
            "INE299W01022": "VIVANTA.BSE",          # Vivanta Industries
            "INE945P01024": "WARDWIZARD.BSE",       # Wardwizard Innovations
            "INE0KQN01018": "BAJEL.BSE",            # Bajel Projects
            "INE01P501012": "XELPMOC.BSE",          # Xelpmoc Design
             
            # ETFs / Mutual Funds (From User Logs)
            "INF204KB14I2": "NIFTYBEES.BSE",        # Nippon India ETF Nifty BeES
            "INF179KC1JY6": "HDFCSENSEX.BSE",       # HDFC Index Fund (Mapped to closest ticker)
            "INF204K01K15": "NIPPONSMALL.BSE",      # Nippon Small Cap (Mapped to closest ticker)
        }
        
        symbol = isin_map.get(isin, f"{isin}.BSE")
        
        # Don't add if already present
        for h in holdings:
            if h["symbol"] == symbol:
                return

        print(f"[DepositoryService] Found holding: {symbol}, Qty: {quantity}")
        holdings.append({
            "symbol": symbol,
            "quantity": quantity,
            "avg_cost": round(avg_cost, 2),
            "source": "CAS"
        })
        
        # Remove duplicates based on symbol
        seen = set()
        unique_holdings = []
        for h in holdings:
            if h["symbol"] not in seen:
                seen.add(h["symbol"])
                unique_holdings.append(h)
        
        return unique_holdings

    @classmethod
    async def fetch_holdings_by_demat(cls, demat_id: str) -> List[Dict]:
        """
        Simulates fetching holdings from CDSL/NSDL using a 16-digit Demat ID.
        """
        if not demat_id:
            return []
            
        print(f"[DepositoryService] Searching holdings for Demat ID: {demat_id}")
        
        if demat_id in cls.DEP_SEED_DATA:
            data = cls.DEP_SEED_DATA[demat_id]
            for item in data:
                item["source"] = "CDSL"
            return data
        
        if len(str(demat_id)) >= 8:
            data = cls.DEP_SEED_DATA["default"]
            for item in data:
                item["source"] = "CDSL"
            return data
            
        return []
