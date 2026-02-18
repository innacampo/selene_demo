#!/usr/bin/env python3
"""
Basic SELENE Usage Example

This example demonstrates how to use SELENE's core functionality
programmatically without the Streamlit UI.
"""

from selene.core.context_builder import build_user_context
from selene.core.context_builder_multi_agent import load_user_profile
from selene.core.deterministic_analysis import DeterministicAnalyzer
from selene.storage.data_manager import load_pulse_history


def main():
    """Run basic SELENE functionality examples."""

    print("=" * 60)
    print("SELENE Basic Usage Example")
    print("=" * 60)

    # Example 1: Load user profile
    print("\n1. Loading user profile...")
    try:
        profile = load_user_profile()
        if profile:
            print(f"   ✓ Profile loaded: Stage = {profile.get('stage', 'Unknown')}")
        else:
            print("   ℹ No profile found (run onboarding first)")
    except Exception as e:
        print(f"   ✗ Error: {e}")

    # Example 2: Load pulse history
    print("\n2. Loading pulse history...")
    try:
        pulse_data = load_pulse_history()
        print(f"   ✓ Loaded {len(pulse_data)} pulse entries")
        if pulse_data:
            latest = pulse_data[-1]
            print(f"   Latest entry: {latest.get('date', 'Unknown date')}")
    except Exception as e:
        print(f"   ✗ Error: {e}")

    # Example 3: Analyze symptoms
    print("\n3. Analyzing symptoms...")
    try:
        if pulse_data:
            analyzer = DeterministicAnalyzer(pulse_data[-14:])  # Last 14 days
            analysis = analyzer.compute_symptom_statistics()
            print("   ✓ Analysis complete")
            print(f"   Symptoms analyzed: {len(analysis)}")
        else:
            print("   ℹ No pulse data available for analysis")
    except Exception as e:
        print(f"   ✗ Error: {e}")

    # Example 4: Build user context
    print("\n4. Building user context...")
    try:
        context = build_user_context(include_profile=True, include_pulse=True)
        print(f"   ✓ Context built ({len(context)} characters)")
        if context:
            print(f"   Preview: {context[:100]}...")
    except Exception as e:
        print(f"   ✗ Error: {e}")

    # Example 5: Risk assessment
    print("\n5. Assessing risk...")
    try:
        if pulse_data:
            analyzer = DeterministicAnalyzer(pulse_data)
            risk = analyzer.assess_risk_level(pulse_data)
            print("   ✓ Risk assessment complete")
            print(f"   Risk level: {risk.get('risk_level', 'Unknown')}")
            if risk.get("risk_flags"):
                print(f"   Flags: {', '.join(risk['risk_flags'])}")
        else:
            print("   ℹ No pulse data available for risk assessment")
    except Exception as e:
        print(f"   ✗ Error: {e}")

    print("\n" + "=" * 60)
    print("Example complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("  - Run the full app: streamlit run app.py")
    print("  - View other examples in examples/")
    print("  - Read the docs: docs/")
    print()


if __name__ == "__main__":
    main()
