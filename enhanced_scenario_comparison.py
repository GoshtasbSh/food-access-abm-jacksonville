"""
Enhanced Scenario Comparison and Analysis
========================================

This module provides comprehensive comparison and analysis capabilities
for the Enhanced Mesa-Geo food access scenarios.
"""

from enhanced_scenario_1 import create_enhanced_scenario_1, EnhancedScenario1Model
from enhanced_scenario_2 import create_enhanced_scenario_2, EnhancedScenario2Model
from enhanced_mesa_geo_model import SimulationConfig
import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple, List
import time

class ScenarioComparison:
    """
    Comprehensive scenario comparison class for analyzing
    Enhanced Mesa-Geo food access scenarios
    """
    
    def __init__(self):
        self.scenario1_results = None
        self.scenario2_results = None
        self.comparison_data = None
    
    def run_scenario_comparison(self, config: SimulationConfig = None) -> Dict[str, Any]:
        """
        Run both scenarios and generate comprehensive comparison
        
        Args:
            config: Simulation configuration object with all parameters
        
        Returns:
            Comprehensive comparison results
        """
        
        if config is None:
            config = SimulationConfig()
        
        print("🚀 Enhanced Mesa-Geo Scenario Comparison Analysis")
        print("=" * 60)
        print(f"   Consumers: {config.num_consumers}")
        print(f"   Simulation Days: {config.simulation_days}")
        
        # Run Scenario 1
        print("\n📊 Running Enhanced Scenario 1: New Grocery Store...")
        start_time = time.time()
        
        scenario1 = create_enhanced_scenario_1(config)
        
        self._run_simulation(scenario1, config.simulation_days, "Scenario 1")
        scenario1_time = time.time() - start_time
        
        self.scenario1_results = scenario1.analyze_scenario_outcomes()
        self.scenario1_results['runtime_seconds'] = scenario1_time
        
        # Run Scenario 2
        print("\n📊 Running Enhanced Scenario 2: Food Hub + Corner Stores...")
        start_time = time.time()
        
        scenario2 = create_enhanced_scenario_2(config)
        
        self._run_simulation(scenario2, config.simulation_days, "Scenario 2")
        scenario2_time = time.time() - start_time
        
        self.scenario2_results = scenario2.analyze_network_performance()
        self.scenario2_results['runtime_seconds'] = scenario2_time
        
        # Generate comprehensive comparison
        print("\n📈 Generating comprehensive comparison analysis...")
        self.comparison_data = self._generate_comprehensive_comparison()
        
        return self.comparison_data
    
    def _run_simulation(self, model, days: int, scenario_name: str):
        """Run simulation with progress updates"""
        print(f"   ⏳ Running {scenario_name} simulation for {days} days...")
        
        for day in range(days):
            model.step()
            if day % 5 == 0 or day == days - 1:  # Progress every 5 days
                satisfaction = model._calculate_satisfaction_rate()
                print(f"      Day {day + 1:2d}: Satisfaction {satisfaction:.2%}")
        
        print(f"   ✅ {scenario_name} simulation complete")
    
    def _generate_comprehensive_comparison(self) -> Dict[str, Any]:
        """Generate comprehensive comparison between scenarios"""
        
        s1_metrics = self.scenario1_results['overall_metrics']
        s2_metrics = self.scenario2_results['overall_metrics']
        
        # Core performance comparison
        performance_comparison = {
            'satisfaction_rate': {
                'scenario1': s1_metrics['avg_satisfaction_rate'],
                'scenario2': s2_metrics['avg_satisfaction_rate'],
                'improvement': s2_metrics['avg_satisfaction_rate'] - s1_metrics['avg_satisfaction_rate'],
                'percent_improvement': ((s2_metrics['avg_satisfaction_rate'] - s1_metrics['avg_satisfaction_rate']) / s1_metrics['avg_satisfaction_rate'] * 100) if s1_metrics['avg_satisfaction_rate'] > 0 else 0
            },
            'food_insecurity_rate': {
                'scenario1': s1_metrics['avg_food_insecurity_rate'],
                'scenario2': s2_metrics['avg_food_insecurity_rate'],
                'improvement': s1_metrics['avg_food_insecurity_rate'] - s2_metrics['avg_food_insecurity_rate'],  # Lower is better
                'percent_improvement': ((s1_metrics['avg_food_insecurity_rate'] - s2_metrics['avg_food_insecurity_rate']) / s1_metrics['avg_food_insecurity_rate'] * 100) if s1_metrics['avg_food_insecurity_rate'] > 0 else 0
            },
            'travel_distance': {
                'scenario1': s1_metrics['avg_travel_distance'],
                'scenario2': s2_metrics['avg_travel_distance'],
                'change': s2_metrics['avg_travel_distance'] - s1_metrics['avg_travel_distance'],
                'percent_change': ((s2_metrics['avg_travel_distance'] - s1_metrics['avg_travel_distance']) / s1_metrics['avg_travel_distance'] * 100) if s1_metrics['avg_travel_distance'] > 0 else 0
            },
            'spatial_equity': {
                'scenario1': s1_metrics['spatial_equity_index'],
                'scenario2': s2_metrics['spatial_equity_index'],
                'improvement': s1_metrics['spatial_equity_index'] - s2_metrics['spatial_equity_index'],  # Lower is better
                'percent_improvement': ((s1_metrics['spatial_equity_index'] - s2_metrics['spatial_equity_index']) / s1_metrics['spatial_equity_index'] * 100) if s1_metrics['spatial_equity_index'] > 0 else 0
            }
        }
        
        # Demographic equity comparison
        equity_comparison = self._compare_demographic_equity()
        
        # Accessibility comparison
        accessibility_comparison = self._compare_accessibility_patterns()
        
        # Economic comparison
        economic_comparison = self._compare_economic_impacts()
        
        # Infrastructure comparison
        infrastructure_comparison = self._compare_infrastructure_requirements()
        
        # Risk and resilience comparison
        resilience_comparison = self._compare_resilience_factors()
        
        # Overall recommendation
        recommendation = self._generate_recommendation()
        
        return {
            'comparison_summary': {
                'scenario1_name': 'New Grocery Store',
                'scenario2_name': 'Food Hub + Corner Stores Network',
                'simulation_parameters': {
                    'consumers': self.scenario1_results['num_consumers'],
                    'simulation_days': self.scenario1_results['simulation_days']
                }
            },
            'performance_comparison': performance_comparison,
            'equity_comparison': equity_comparison,
            'accessibility_comparison': accessibility_comparison,
            'economic_comparison': economic_comparison,
            'infrastructure_comparison': infrastructure_comparison,
            'resilience_comparison': resilience_comparison,
            'recommendation': recommendation,
            'runtime_comparison': {
                'scenario1_seconds': self.scenario1_results['runtime_seconds'],
                'scenario2_seconds': self.scenario2_results['runtime_seconds']
            }
        }
    
    def _compare_demographic_equity(self) -> Dict[str, Any]:
        """Compare demographic equity between scenarios"""
        
        s1_demo = self.scenario1_results['demographic_analysis']
        s2_demo = self.scenario2_results['demographic_analysis']
        
        equity_comparison = {}
        
        # Income-based comparison
        for income_level in ['low', 'medium', 'high']:
            key = f'income_{income_level}'
            if key in s1_demo and key in s2_demo:
                s1_satisfaction = s1_demo[key]['satisfaction_rate']
                s2_satisfaction = s2_demo[key]['satisfaction_rate']
                
                equity_comparison[f'{income_level}_income'] = {
                    'scenario1_satisfaction': s1_satisfaction,
                    'scenario2_satisfaction': s2_satisfaction,
                    'improvement': s2_satisfaction - s1_satisfaction,
                    'percent_improvement': ((s2_satisfaction - s1_satisfaction) / s1_satisfaction * 100) if s1_satisfaction > 0 else 0
                }
        
        # Car ownership comparison (demographic_analysis uses 'vehicle_availability')
        if 'vehicle_availability' in s1_demo and 'vehicle_availability' in s2_demo:
            equity_comparison['car_ownership_equity'] = {
                'scenario1_gap': s1_demo['vehicle_availability']['with_car']['satisfaction_rate'] - s1_demo['vehicle_availability']['without_car']['satisfaction_rate'],
                'scenario2_gap': s2_demo['vehicle_availability']['with_car']['satisfaction_rate'] - s2_demo['vehicle_availability']['without_car']['satisfaction_rate'],
                'equity_improvement': (s1_demo['vehicle_availability']['with_car']['satisfaction_rate'] - s1_demo['vehicle_availability']['without_car']['satisfaction_rate']) - (s2_demo['vehicle_availability']['with_car']['satisfaction_rate'] - s2_demo['vehicle_availability']['without_car']['satisfaction_rate'])
            }
        
        return equity_comparison
    
    def _compare_accessibility_patterns(self) -> Dict[str, Any]:
        """Compare accessibility patterns and spatial coverage"""
        
        s1_spatial = self.scenario1_results['spatial_analysis']
        s2_spatial = self.scenario2_results['spatial_analysis']
        
        accessibility_comparison = {}
        
        # Provider accessibility comparison
        if 'provider_accessibility' in s1_spatial and 'provider_accessibility' in s2_spatial:
            s1_access = s1_spatial['provider_accessibility']
            s2_access = s2_spatial['provider_accessibility']
            
            accessibility_comparison['spatial_accessibility'] = {
                'avg_distance_to_nearest': {
                    'scenario1': s1_access['avg_distance_to_nearest'],
                    'scenario2': s2_access['avg_distance_to_nearest'],
                    'improvement': s1_access['avg_distance_to_nearest'] - s2_access['avg_distance_to_nearest']  # Lower is better
                },
                'consumers_within_1km': {
                    'scenario1': s1_access['consumers_within_1km'],
                    'scenario2': s2_access['consumers_within_1km'],
                    'improvement': s2_access['consumers_within_1km'] - s1_access['consumers_within_1km']
                }
            }
        
        # Network-specific metrics for Scenario 2
        if 'network_analysis' in self.scenario2_results:
            network_metrics = self.scenario2_results['network_analysis']['accessibility_metrics']
            accessibility_comparison['network_advantages'] = {
                'consumers_with_multiple_options': network_metrics['consumers_with_multiple_options'],
                'network_redundancy': self.scenario2_results['network_analysis']['network_performance']['network_redundancy'],
                'spatial_coverage': self.scenario2_results['network_analysis']['network_performance']['spatial_coverage']
            }
        
        return accessibility_comparison
    
    def _compare_economic_impacts(self) -> Dict[str, Any]:
        """Compare economic impacts and costs"""
        
        # Infrastructure costs (simplified estimates)
        grocery_store_cost = 500000  # $500k estimate for grocery store
        food_hub_cost = 200000      # $200k estimate for food hub
        corner_store_cost = 50000   # $50k estimate per corner store
        
        if 'network_analysis' in self.scenario2_results:
            num_corner_stores = self.scenario2_results['network_analysis']['network_composition']['corner_stores']
            scenario2_infrastructure_cost = food_hub_cost + (num_corner_stores * corner_store_cost)
        else:
            scenario2_infrastructure_cost = food_hub_cost + (6 * corner_store_cost)  # Default estimate
        
        # Operating efficiency comparison
        s1_total_capacity = sum(p['capacity'] for p in [{'capacity': 600}])  # Simplified
        s2_total_capacity = 300 + (6 * 60)  # Food hub + corner stores
        
        economic_comparison = {
            'infrastructure_costs': {
                'scenario1_estimated_cost': grocery_store_cost,
                'scenario2_estimated_cost': scenario2_infrastructure_cost,
                'cost_difference': scenario2_infrastructure_cost - grocery_store_cost
            },
            'operational_efficiency': {
                'scenario1_capacity': s1_total_capacity,
                'scenario2_capacity': s2_total_capacity,
                'capacity_difference': s2_total_capacity - s1_total_capacity
            },
            'cost_per_consumer_served': {
                'scenario1': grocery_store_cost / (self.scenario1_results['overall_metrics']['avg_satisfaction_rate'] * self.scenario1_results['num_consumers']),
                'scenario2': scenario2_infrastructure_cost / (self.scenario2_results['overall_metrics']['avg_satisfaction_rate'] * self.scenario2_results['num_consumers'])
            }
        }
        
        return economic_comparison
    
    def _compare_infrastructure_requirements(self) -> Dict[str, Any]:
        """Compare infrastructure requirements and complexity"""
        
        return {
            'scenario1_infrastructure': {
                'facilities_required': 1,
                'facility_types': ['Large Grocery Store'],
                'complexity_level': 'Low',
                'maintenance_requirements': 'Moderate',
                'staffing_requirements': 'High (centralized)'
            },
            'scenario2_infrastructure': {
                'facilities_required': 7,  # 1 food hub + 6 corner stores
                'facility_types': ['Food Hub', 'Corner Stores'],
                'complexity_level': 'High',
                'maintenance_requirements': 'High (distributed)',
                'staffing_requirements': 'Moderate (distributed)'
            },
            'trade_offs': {
                'scenario1_advantages': ['Lower complexity', 'Centralized management', 'Economies of scale'],
                'scenario2_advantages': ['Distributed access', 'Community integration', 'Redundancy'],
                'scenario1_disadvantages': ['Single point of failure', 'Distance barriers', 'Limited accessibility'],
                'scenario2_disadvantages': ['Higher complexity', 'Coordination challenges', 'Higher setup costs']
            }
        }
    
    def _compare_resilience_factors(self) -> Dict[str, Any]:
        """Compare resilience and risk factors"""
        
        return {
            'risk_assessment': {
                'scenario1_risks': {
                    'single_point_failure': 'High - if store closes, entire area loses access',
                    'capacity_bottleneck': 'High - limited by single store capacity',
                    'accessibility_barriers': 'High - distance barriers for some consumers'
                },
                'scenario2_risks': {
                    'coordination_complexity': 'Medium - requires coordination between facilities',
                    'distributed_management': 'Medium - multiple facilities to manage',
                    'supply_chain_complexity': 'Medium - food hub supply coordination'
                }
            },
            'resilience_factors': {
                'scenario1_resilience': {
                    'redundancy': 'Low',
                    'adaptability': 'Low',
                    'community_integration': 'Medium'
                },
                'scenario2_resilience': {
                    'redundancy': 'High',
                    'adaptability': 'High',
                    'community_integration': 'High'
                }
            }
        }
    
    def _generate_recommendation(self) -> Dict[str, Any]:
        """Generate recommendation based on comparison analysis"""
        
        # Calculate overall scores
        s1_satisfaction = self.scenario1_results['overall_metrics']['avg_satisfaction_rate']
        s2_satisfaction = self.scenario2_results['overall_metrics']['avg_satisfaction_rate']
        
        s1_equity = 1 - self.scenario1_results['overall_metrics']['spatial_equity_index']  # Higher is better
        s2_equity = 1 - self.scenario2_results['overall_metrics']['spatial_equity_index']
        
        s1_accessibility = 1 / (1 + self.scenario1_results['overall_metrics']['avg_travel_distance'])  # Lower distance is better
        s2_accessibility = 1 / (1 + self.scenario2_results['overall_metrics']['avg_travel_distance'])
        
        # Weighted scoring (can be adjusted based on priorities)
        weights = {'satisfaction': 0.4, 'equity': 0.3, 'accessibility': 0.3}
        
        s1_score = (s1_satisfaction * weights['satisfaction'] + 
                   s1_equity * weights['equity'] + 
                   s1_accessibility * weights['accessibility'])
        
        s2_score = (s2_satisfaction * weights['satisfaction'] + 
                   s2_equity * weights['equity'] + 
                   s2_accessibility * weights['accessibility'])
        
        # Determine recommendation
        if s2_score > s1_score * 1.1:  # 10% threshold for clear winner
            recommended_scenario = 'scenario2'
            confidence = 'High'
        elif s1_score > s2_score * 1.1:
            recommended_scenario = 'scenario1'
            confidence = 'High'
        else:
            recommended_scenario = 'scenario2' if s2_score > s1_score else 'scenario1'
            confidence = 'Medium'
        
        return {
            'recommended_scenario': recommended_scenario,
            'confidence_level': confidence,
            'scenario_scores': {
                'scenario1_total_score': s1_score,
                'scenario2_total_score': s2_score,
                'score_difference': abs(s2_score - s1_score)
            },
            'key_decision_factors': self._identify_key_decision_factors(),
            'implementation_considerations': self._get_implementation_considerations(recommended_scenario)
        }
    
    def _identify_key_decision_factors(self) -> List[str]:
        """Identify key factors that should drive the decision"""
        
        factors = []
        
        # Check satisfaction improvement
        satisfaction_improvement = (self.scenario2_results['overall_metrics']['avg_satisfaction_rate'] - 
                                  self.scenario1_results['overall_metrics']['avg_satisfaction_rate'])
        
        if satisfaction_improvement > 0.05:  # 5% improvement threshold
            factors.append(f"Scenario 2 provides {satisfaction_improvement:.1%} higher satisfaction rate")
        
        # Check equity improvement
        equity_improvement = (self.scenario1_results['overall_metrics']['spatial_equity_index'] - 
                            self.scenario2_results['overall_metrics']['spatial_equity_index'])
        
        if equity_improvement > 0.1:  # 10% equity improvement threshold
            factors.append(f"Scenario 2 provides better spatial equity (lower inequality)")
        
        # Check resilience
        factors.append("Scenario 2 offers higher resilience through network redundancy")
        
        # Check cost-effectiveness
        factors.append("Consider implementation costs and long-term sustainability")
        
        return factors
    
    def _get_implementation_considerations(self, recommended_scenario: str) -> List[str]:
        """Get implementation considerations for the recommended scenario"""
        
        if recommended_scenario == 'scenario1':
            return [
                "Focus on optimal grocery store location for maximum accessibility",
                "Ensure adequate store capacity to meet demand",
                "Consider transportation solutions for consumers without cars",
                "Plan for potential expansion if demand exceeds capacity"
            ]
        else:
            return [
                "Develop coordination mechanisms between food hub and corner stores",
                "Ensure adequate supply chain management for distributed network",
                "Consider phased implementation starting with highest-impact locations",
                "Establish community partnerships for corner store operations",
                "Plan for ongoing coordination and management overhead"
            ]
    
    def generate_comparison_report(self) -> str:
        """Generate a comprehensive text report of the scenario comparison"""
        
        if self.comparison_data is None:
            return "No comparison data available. Please run scenario comparison first."
        
        comp = self.comparison_data
        perf = comp['performance_comparison']
        
        report = f"""
Enhanced Mesa-Geo Food Access Scenario Comparison Report
=======================================================

Simulation Overview:
- Consumers: {comp['comparison_summary']['simulation_parameters']['consumers']}
- Simulation Days: {comp['comparison_summary']['simulation_parameters']['simulation_days']}
- Scenario 1: {comp['comparison_summary']['scenario1_name']}
- Scenario 2: {comp['comparison_summary']['scenario2_name']}

PERFORMANCE COMPARISON
=====================

Satisfaction Rate:
- Scenario 1: {perf['satisfaction_rate']['scenario1']:.2%}
- Scenario 2: {perf['satisfaction_rate']['scenario2']:.2%}
- Improvement: {perf['satisfaction_rate']['improvement']:+.2%} ({perf['satisfaction_rate']['percent_improvement']:+.1f}%)

Food Insecurity Rate:
- Scenario 1: {perf['food_insecurity_rate']['scenario1']:.2%}
- Scenario 2: {perf['food_insecurity_rate']['scenario2']:.2%}
- Improvement: {perf['food_insecurity_rate']['improvement']:+.2%} ({perf['food_insecurity_rate']['percent_improvement']:+.1f}%)

Average Travel Distance:
- Scenario 1: {perf['travel_distance']['scenario1']:.2f} km
- Scenario 2: {perf['travel_distance']['scenario2']:.2f} km
- Change: {perf['travel_distance']['change']:+.2f} km ({perf['travel_distance']['percent_change']:+.1f}%)

Spatial Equity Index (lower = more equitable):
- Scenario 1: {perf['spatial_equity']['scenario1']:.3f}
- Scenario 2: {perf['spatial_equity']['scenario2']:.3f}
- Improvement: {perf['spatial_equity']['improvement']:+.3f} ({perf['spatial_equity']['percent_improvement']:+.1f}%)

RECOMMENDATION
=============

Recommended Scenario: {comp['recommendation']['recommended_scenario'].upper()}
Confidence Level: {comp['recommendation']['confidence_level']}

Key Decision Factors:
{chr(10).join(f"• {factor}" for factor in comp['recommendation']['key_decision_factors'])}

Implementation Considerations:
{chr(10).join(f"• {consideration}" for consideration in comp['recommendation']['implementation_considerations'])}

SUMMARY
=======

Based on the comprehensive analysis, {'Scenario 2 (Food Hub + Corner Stores)' if comp['recommendation']['recommended_scenario'] == 'scenario2' else 'Scenario 1 (New Grocery Store)'} 
is recommended for implementation in Health Zone 1, Jacksonville FL.

This recommendation is based on superior performance in key metrics including satisfaction rate, 
spatial equity, and network resilience, while considering implementation complexity and costs.
"""
        
        return report

# Convenience function for quick comparison
def run_enhanced_scenario_comparison(config: SimulationConfig = None) -> ScenarioComparison:
    """
    Quick function to run scenario comparison with configuration
    
    Args:
        config: Simulation configuration object with all parameters
    
    Returns:
        ScenarioComparison object with complete analysis
    """
    
    comparison = ScenarioComparison()
    comparison.run_scenario_comparison(config)
    
    return comparison

# Example usage
if __name__ == "__main__":
    print("🚀 Enhanced Mesa-Geo Scenario Comparison")
    print("=" * 50)
    
    # Create configuration and run comparison
    config = SimulationConfig(num_consumers=300, simulation_days=14)
    comparison = run_enhanced_scenario_comparison(config)
    
    # Print summary results
    print(f"\n📊 Comparison Complete!")
    
    perf = comparison.comparison_data['performance_comparison']
    print(f"\n📈 Key Results:")
    print(f"   Satisfaction Rate - S1: {perf['satisfaction_rate']['scenario1']:.2%}, S2: {perf['satisfaction_rate']['scenario2']:.2%}")
    print(f"   Food Insecurity - S1: {perf['food_insecurity_rate']['scenario1']:.2%}, S2: {perf['food_insecurity_rate']['scenario2']:.2%}")
    print(f"   Spatial Equity - S1: {perf['spatial_equity']['scenario1']:.3f}, S2: {perf['spatial_equity']['scenario2']:.3f}")
    
    rec = comparison.comparison_data['recommendation']
    print(f"\n🎯 Recommendation: {rec['recommended_scenario'].upper()} ({rec['confidence_level']} confidence)")
    
    print("\n📋 Generate full report with: comparison.generate_comparison_report()")
    print("✅ Enhanced scenario comparison complete!") 