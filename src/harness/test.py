def two_sum(nums, target):
    num_map = {}
    for i, num in enumerate(nums):
        complement = target - num
        if complement in num_map:
            return [num_map[complement], i]
        num_map[num] = i
    return []

import unittest

class TestTwoSum(unittest.TestCase):
    def test_case_1(self):
        self.assertEqual(two_sum([2,7,11,15], 9), [0,1])
    
    def test_case_2(self):
        self.assertEqual(two_sum([3,2,4], 6), [1,2])
    
    def test_negative_numbers(self):
        self.assertEqual(two_sum([-1,0], -1), [0,1])
    
    def test_duplicates(self):
        self.assertEqual(two_sum([3,3], 6), [0,1])

if __name__ == '__main__':
    unittest.main()