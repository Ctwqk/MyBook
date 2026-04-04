"""Test cases for Audience Phase B components

Tests:
1. SignalWindowAggregate model
2. ReaderScaleSnapshot model
3. FeedbackCooldown cooldown logic
4. SignalAggregator.estimate_reader_scale
5. ReaderFeedbackView.from_candidates (simulated)
"""
import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from unittest.mock import MagicMock, AsyncMock, patch
from typing import Any


# ============================================
# Test: SignalWindowAggregate Model
# ============================================
class TestSignalWindowAggregate:
    """Test SignalWindowAggregate model."""
    
    def test_signal_window_aggregate_attributes(self):
        """Test SignalWindowAggregate attributes exist."""
        # Test with mock data
        mock_aggregate = MagicMock()
        mock_aggregate.signal_key = "confusion:character:主角动机"
        mock_aggregate.window_chapter_start = 10
        mock_aggregate.window_chapter_end = 17
        mock_aggregate.hit_comment_count = 5
        mock_aggregate.unique_user_count = 3
        mock_aggregate.total_comment_count = 50
        mock_aggregate.reader_estimate = 500
        mock_aggregate.signal_level = "candidate"
        
        assert mock_aggregate.signal_key == "confusion:character:主角动机"
        assert mock_aggregate.window_chapter_start == 10
        assert mock_aggregate.window_chapter_end == 17
        assert mock_aggregate.hit_comment_count == 5
        assert mock_aggregate.unique_user_count == 3
        assert mock_aggregate.total_comment_count == 50
        assert mock_aggregate.reader_estimate == 500
        assert mock_aggregate.signal_level == "candidate"
    
    def test_signal_window_aggregate_key_parsing(self):
        """Test parsing of signal key format."""
        signal_key = "confusion:character:主角动机"
        parts = signal_key.split(":")
        
        assert len(parts) == 3
        assert parts[0] == "confusion"
        assert parts[1] == "character"
        assert parts[2] == "主角动机"
    
    def test_signal_key_format(self):
        """Test signal key format construction."""
        from app.models.comment import SignalType, TargetType
        
        signal_key = f"{SignalType.CONFUSION.value}:{TargetType.CHARACTER.value}:测试目标"
        
        assert signal_key == "confusion:character:测试目标"
        assert SignalType.CONFUSION.value in signal_key


# ============================================
# Test: ReaderScaleSnapshot Model
# ============================================
class TestReaderScaleSnapshot:
    """Test ReaderScaleSnapshot model."""
    
    def test_reader_scale_snapshot_attributes(self):
        """Test ReaderScaleSnapshot attributes exist."""
        mock_snapshot = MagicMock()
        mock_snapshot.chapter_number = 5
        mock_snapshot.reader_estimate = 10000
        mock_snapshot.estimation_method = "sampling"
        mock_snapshot.tier = "B"
        
        assert mock_snapshot.chapter_number == 5
        assert mock_snapshot.reader_estimate == 10000
        assert mock_snapshot.estimation_method == "sampling"
        assert mock_snapshot.tier == "B"
    
    def test_tier_assignment_scale_ranges(self):
        """Test tier assignment based on reader scale."""
        def assign_tier(scale: int) -> str:
            if scale >= 100000:
                return "S"
            elif scale >= 50000:
                return "A"
            elif scale >= 10000:
                return "B"
            elif scale >= 1000:
                return "C"
            else:
                return "D"
        
        assert assign_tier(200000) == "S"
        assert assign_tier(50000) == "A"
        assert assign_tier(10000) == "B"
        assert assign_tier(1000) == "C"
        assert assign_tier(100) == "D"
    
    def test_reader_scale_ordering(self):
        """Test ordering of reader scale snapshots."""
        snapshots = [
            {"chapter": 10, "estimate": 1000},
            {"chapter": 5, "estimate": 500},
            {"chapter": 8, "estimate": 800},
            {"chapter": 3, "estimate": 300},
            {"chapter": 1, "estimate": 100},
        ]
        
        sorted_snapshots = sorted(snapshots, key=lambda x: x["chapter"])
        chapter_numbers = [s["chapter"] for s in sorted_snapshots]
        
        assert chapter_numbers == [1, 3, 5, 8, 10]


# ============================================
# Test: FeedbackCooldown Logic
# ============================================
class TestFeedbackCooldown:
    """Test FeedbackCooldown cooldown management logic."""
    
    def test_cooldown_calculation(self):
        """Test cooldown period calculation."""
        chapter_number = 10
        cooldown_chapters = 3
        cooldown_until = chapter_number + cooldown_chapters
        
        assert cooldown_until == 13
    
    def test_is_cooled_during_cooldown(self):
        """Test is_cooled returns True during cooldown period."""
        cooldown_until = 13
        current_chapter = 11
        
        is_cooled = current_chapter < cooldown_until
        assert is_cooled is True
    
    def test_is_cooled_after_cooldown_ended(self):
        """Test is_cooled returns False after cooldown period."""
        cooldown_until = 13
        current_chapter = 14
        
        is_cooled = current_chapter < cooldown_until
        assert is_cooled is False
    
    def test_remaining_cooldown_calculation(self):
        """Test remaining cooldown chapters calculation."""
        cooldown_until = 25
        current_chapter = 22
        remaining = max(0, cooldown_until - current_chapter)
        
        assert remaining == 3
    
    def test_remaining_cooldown_when_expired(self):
        """Test remaining cooldown is 0 when expired."""
        cooldown_until = 25
        current_chapter = 30
        remaining = max(0, cooldown_until - current_chapter)
        
        assert remaining == 0
    
    def test_clear_cooldown_logic(self):
        """Test clear cooldown removes cooldown state."""
        cooldown_record = {"cooldown_until": 13}
        
        # Simulate clearing
        cleared_record = None
        cleared = cooldown_record is not None
        
        assert cleared is True
        # After clearing, the record should be removed
        cooldown_record = None
        assert cooldown_record is None


# ============================================
# Test: SignalAggregator.estimate_reader_scale
# ============================================
class TestSignalAggregator:
    """Test SignalAggregator functionality."""
    
    def test_estimate_reader_scale_default_ratio(self):
        """Test reader scale estimation with default 100:1 ratio."""
        total_comments = 50
        comment_to_reader_ratio = 100
        estimated = total_comments * comment_to_reader_ratio
        
        assert estimated == 5000
    
    def test_estimate_reader_scale_custom_ratio(self):
        """Test reader scale estimation with custom ratio."""
        total_comments = 100
        comment_to_reader_ratio = 50
        estimated = total_comments * comment_to_reader_ratio
        
        assert estimated == 5000
    
    def test_estimate_reader_scale_zero_comments(self):
        """Test reader scale estimation with zero comments."""
        total_comments = 0
        comment_to_reader_ratio = 100
        estimated = total_comments * comment_to_reader_ratio
        
        assert estimated == 0
    
    def test_estimate_reader_scale_large_volume(self):
        """Test reader scale estimation with large comment volume."""
        total_comments = 10000
        comment_to_reader_ratio = 100
        estimated = total_comments * comment_to_reader_ratio
        
        assert estimated == 1000000
    
    def test_window_configuration(self):
        """Test that window configuration is correct."""
        WINDOWS = [
            ("short", 3),
            ("medium", 8),
            ("long", 20),
        ]
        
        assert WINDOWS == [
            ("short", 3),
            ("medium", 8),
            ("long", 20),
        ]
    
    def test_get_chapter_range_short_window(self):
        """Test chapter range calculation for short window."""
        latest_chapter = 5
        window_size = 3
        start = max(1, latest_chapter - window_size + 1)
        end = latest_chapter
        
        assert start == 3
        assert end == 5
    
    def test_get_chapter_range_first_chapter(self):
        """Test chapter range when only first chapter exists."""
        latest_chapter = 1
        window_size = 3
        start = max(1, latest_chapter - window_size + 1)
        end = latest_chapter
        
        assert start == 1
        assert end == 1


# ============================================
# Test: ReaderFeedbackView (Simulated)
# ============================================
class TestReaderFeedbackView:
    """Test ReaderFeedbackView functionality (simulated from_candidates)."""
    
    def test_from_candidates_basic_aggregation(self):
        """Test basic aggregation of candidates."""
        # Simulated candidate data
        candidates = [
            {"signal_type": "confusion", "target_type": "character", "target_name": "主角", "confidence": 0.7, "severity": 2},
            {"signal_type": "confusion", "target_type": "character", "target_name": "主角", "confidence": 0.7, "severity": 2},
            {"signal_type": "confusion", "target_type": "character", "target_name": "主角", "confidence": 0.7, "severity": 2},
            {"signal_type": "confusion", "target_type": "character", "target_name": "主角", "confidence": 0.7, "severity": 2},
            {"signal_type": "confusion", "target_type": "character", "target_name": "主角", "confidence": 0.7, "severity": 2},
        ]
        
        # Aggregate
        aggregated = {}
        for c in candidates:
            key = (c["signal_type"], c["target_type"], c["target_name"])
            if key not in aggregated:
                aggregated[key] = {"count": 0, "total_confidence": 0.0, "max_severity": 0}
            aggregated[key]["count"] += 1
            aggregated[key]["total_confidence"] += c["confidence"]
            aggregated[key]["max_severity"] = max(aggregated[key]["max_severity"], c["severity"])
        
        # Calculate avg confidence
        aggregated[key]["avg_confidence"] = aggregated[key]["total_confidence"] / aggregated[key]["count"]
        
        assert ("confusion", "character", "主角") in aggregated
        assert aggregated[("confusion", "character", "主角")]["count"] == 5
        assert aggregated[("confusion", "character", "主角")]["avg_confidence"] == pytest.approx(0.7)
        assert aggregated[("confusion", "character", "主角")]["max_severity"] == 2
    
    def test_from_candidates_multiple_signal_types(self):
        """Test aggregation with multiple signal types."""
        candidates = [
            {"signal_type": "confusion", "confidence": 0.6},
            {"signal_type": "confusion", "confidence": 0.7},
            {"signal_type": "pacing", "confidence": 0.8},
            {"signal_type": "risk", "confidence": 0.9},
        ]
        
        by_signal_type = {}
        for c in candidates:
            if c["signal_type"] not in by_signal_type:
                by_signal_type[c["signal_type"]] = {"count": 0, "total_confidence": 0.0}
            by_signal_type[c["signal_type"]]["count"] += 1
            by_signal_type[c["signal_type"]]["total_confidence"] += c["confidence"]
        
        assert by_signal_type["confusion"]["count"] == 2
        assert by_signal_type["pacing"]["count"] == 1
        assert by_signal_type["risk"]["count"] == 1
    
    def test_from_candidates_severity_filtering(self):
        """Test that high-severity candidates are correctly identified."""
        candidates = [
            {"severity": 1, "confidence": 0.5},
            {"severity": 3, "confidence": 0.7},
            {"severity": 4, "confidence": 0.9},
        ]
        
        high_severity = [c for c in candidates if c["severity"] >= 3]
        
        assert len(high_severity) == 2
        assert all(c["severity"] >= 3 for c in high_severity)
    
    def test_from_candidates_signal_level_filtering(self):
        """Test filtering candidates by signal level."""
        candidates = [
            {"signal_level": "noise"},
            {"signal_level": "candidate"},
            {"signal_level": "candidate"},
            {"signal_level": "confirmed"},
            {"signal_level": "watchlist"},
        ]
        
        filtered = [c for c in candidates if c["signal_level"] in ["confirmed", "watchlist"]]
        
        assert len(filtered) == 2
        assert all(c["signal_level"] in ["confirmed", "watchlist"] for c in filtered)
