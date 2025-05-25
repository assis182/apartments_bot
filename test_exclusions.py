import unittest
from src.utils import is_excluded, load_exclusions, add_street_to_exclusions

class TestExclusions(unittest.TestCase):
    def setUp(self):
        # Load current exclusions to verify test data
        self.exclusions = load_exclusions()
        print("\nCurrent exclusions:", self.exclusions)
    
    def test_specific_address_exclusions(self):
        """Test that specific addresses are properly excluded"""
        
        # Test פנקס 67
        listing1 = {
            'address': {
                'street': 'פנקס',
                'number': '67',
            }
        }
        self.assertTrue(is_excluded(listing1), "פנקס 67 should be excluded")
        
        # Test יצחק אפשטיין 7
        listing2 = {
            'address': {
                'street': 'יצחק אפשטיין',
                'number': '7',
            }
        }
        self.assertTrue(is_excluded(listing2), "יצחק אפשטיין 7 should be excluded")
        
        # Test that different number on same street is not excluded
        listing3 = {
            'address': {
                'street': 'פנקס',
                'number': '68',
            }
        }
        self.assertFalse(is_excluded(listing3), "פנקס 68 should not be excluded")
    
    def test_entire_street_exclusion(self):
        """Test that entire street exclusions work properly"""
        
        # Test ויסוצקי street with different numbers
        addresses = ['1', '2', '10', '20A', '100']
        for number in addresses:
            listing = {
                'address': {
                    'street': 'ויסוצקי',
                    'number': number,
                }
            }
            self.assertTrue(
                is_excluded(listing), 
                f"ויסוצקי {number} should be excluded as entire street is blocked"
            )
            
        # Test הירקון street with different numbers
        addresses = ['1', '288', '100', '200A']
        for number in addresses:
            listing = {
                'address': {
                    'street': 'הירקון',
                    'number': number,
                }
            }
            self.assertTrue(
                is_excluded(listing), 
                f"הירקון {number} should be excluded as entire street is blocked"
            )
            
        # Test הירקון with different street name formats
        test_cases = [
            {'street': 'הירקון', 'number': '288'},
            {'street': 'הירקון ', 'number': '288'},  # Extra space
            {'street': ' הירקון', 'number': '288'},  # Leading space
            {'street': 'הירקון', 'number': ' 288'},  # Space in number
            {'street': 'הירקון', 'number': '288 '},  # Trailing space in number
        ]
        
        for test_case in test_cases:
            listing = {
                'address': test_case
            }
            self.assertTrue(
                is_excluded(listing),
                f"הירקון {test_case['number']} with format {test_case} should be excluded"
            )
    
    def test_edge_cases(self):
        """Test edge cases and malformed data"""
        
        # Test with missing street
        listing1 = {
            'address': {
                'number': '67',
            }
        }
        self.assertFalse(is_excluded(listing1), "Listing without street should not be excluded")
        
        # Test with empty street
        listing2 = {
            'address': {
                'street': '',
                'number': '67',
            }
        }
        self.assertFalse(is_excluded(listing2), "Listing with empty street should not be excluded")
        
        # Test with whitespace variations
        listing3 = {
            'address': {
                'street': '  פנקס  ',
                'number': ' 67 ',
            }
        }
        self.assertTrue(is_excluded(listing3), "פנקס 67 with extra whitespace should be excluded")
        
        # Test with None values
        listing4 = {
            'address': {
                'street': None,
                'number': None,
            }
        }
        self.assertFalse(is_excluded(listing4), "Listing with None values should not be excluded")
        
        # Test with malformed address
        listing5 = {
            'address': 'not a dict'
        }
        self.assertFalse(is_excluded(listing5), "Listing with invalid address format should not be excluded")
        
    def test_street_name_variations(self):
        """Test that street name variations are properly handled"""
        # Add הירקון to exclusions if not already there
        add_street_to_exclusions('הירקון', 'Test exclusion')
        
        # Test various street name formats
        test_cases = [
            {'street': 'הירקון', 'number': '288'},
            {'street': 'הירקון ', 'number': '288'},
            {'street': ' הירקון', 'number': '288'},
            {'street': 'הירקון', 'number': ' 288'},
            {'street': 'הירקון', 'number': '288 '},
            {'street': 'הירקון', 'number': ''},
            {'street': 'הירקון', 'number': None},
        ]
        
        for test_case in test_cases:
            listing = {
                'address': test_case
            }
            self.assertTrue(
                is_excluded(listing),
                f"הירקון with format {test_case} should be excluded"
            )

if __name__ == '__main__':
    unittest.main(verbosity=2) 