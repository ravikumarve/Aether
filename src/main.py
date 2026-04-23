"""
AETHER Main Entry Point
Autonomous Environmental & Thermal Habitat Efficiency Regulator
"""

import logging
import sys
import argparse
from datetime import datetime
from dotenv import load_dotenv

# Import AETHER components
from sim_engine import SimPyEnvironment
from mqtt_client import AetherMQTTClient
from orchestrator import AgentsOrchestrator


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('aether.log')
    ]
)
logger = logging.getLogger(__name__)


def main():
    """Main entry point for the AETHER system."""
    
    # Load environment variables
    load_dotenv()
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='AETHER - Autonomous Environmental & Thermal Habitat Efficiency Regulator'
    )
    parser.add_argument(
        '--cycles',
        type=int,
        default=24,
        help='Number of simulation cycles to run (default: 24)'
    )
    parser.add_argument(
        '--no-mqtt',
        action='store_true',
        help='Run without MQTT broker (simulation only)'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    parser.add_argument(
        '--version',
        action='version',
        version='AETHER v1.0.0 - MVP'
    )
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    logger.info("=" * 80)
    logger.info("AETHER - Autonomous Environmental & Thermal Habitat Efficiency Regulator")
    logger.info("=" * 80)
    logger.info(f"Starting at: {datetime.now().isoformat()}")
    logger.info(f"Simulation cycles: {args.cycles}")
    logger.info(f"MQTT enabled: {not args.no_mqtt}")
    logger.info("")
    
    try:
        # Step 1: Initialize SimPy simulation engine
        logger.info("Step 1: Initializing SimPy simulation engine...")
        sim_engine = SimPyEnvironment()
        logger.info("✓ SimPy simulation engine initialized")
        
        # Step 2: Initialize MQTT client (if enabled)
        mqtt_client = None
        if not args.no_mqtt:
            logger.info("Step 2: Initializing MQTT client...")
            mqtt_client = AetherMQTTClient()
            if mqtt_client.connect():
                logger.info("✓ MQTT client connected")
            else:
                logger.warning("⚠ MQTT client connection failed, continuing without MQTT")
                mqtt_client = None
        else:
            logger.info("Step 2: MQTT disabled (simulation only)")
        
        # Step 3: Initialize Agents Orchestrator
        logger.info("Step 3: Initializing Agents Orchestrator...")
        orchestrator = AgentsOrchestrator(sim_engine, mqtt_client)
        logger.info("✓ Agents Orchestrator initialized")
        
        # Step 4: Run the pipeline
        logger.info("")
        logger.info("Step 4: Running AETHER pipeline...")
        logger.info("-" * 80)
        
        completion_report = orchestrator.run_pipeline(max_cycles=args.cycles)
        
        # Step 5: Display results
        logger.info("-" * 80)
        logger.info("")
        logger.info("Step 5: Pipeline completed")
        logger.info("=" * 80)
        
        # Print completion report
        print("\n" + "=" * 80)
        print("AETHER PIPELINE COMPLETION REPORT")
        print("=" * 80)
        print(f"Final Status: {completion_report['final_status']}")
        print(f"Total Cycles: {completion_report['total_cycles']}")
        print(f"Anomalies Handled: {completion_report['anomalies_handled']}")
        print(f"Emergency Responses: {completion_report['emergency_responses']}")
        print(f"Completion Time: {completion_report['completion_time']}")
        print("")
        
        # Print pipeline summary
        print("Pipeline Summary:")
        pipeline_summary = completion_report['pipeline_summary']
        print(f"  Current Phase: {pipeline_summary['current_phase']}")
        print(f"  Cycle Count: {pipeline_summary['cycle_count']}")
        print(f"  Anomalies Detected: {pipeline_summary['anomalies_detected']}")
        print(f"  Emergency Responses: {pipeline_summary['emergency_responses']}")
        print(f"  Uptime: {pipeline_summary['uptime']:.2f} seconds")
        print("")
        
        # Print agent status
        print("Agent Status:")
        for agent_name, agent_status in completion_report['agent_status'].items():
            print(f"  {agent_name.capitalize()}:")
            print(f"    Role: {agent_status['role']}")
            print(f"    Retry Count: {agent_status['retry_count']}")
            if agent_status.get('current_forecast'):
                print(f"    Last Forecast Confidence: {agent_status['current_forecast']['confidence']:.2f}")
            if agent_status.get('current_requirements'):
                print(f"    Last Power Requirement: {agent_status['current_requirements']['power_requirement_watts']:.1f}W")
            if agent_status.get('current_allocation'):
                print(f"    Last Mediation Result: {agent_status['current_allocation']['mediation_result']}")
        print("")
        
        # Print quality gates
        print("Quality Gates:")
        for gate_name, gate_status in completion_report['quality_gates'].items():
            status_symbol = "✓" if gate_status == "pass" else "✗"
            print(f"  {status_symbol} {gate_name}: {gate_status.upper()}")
        print("")
        
        # Print environmental summary
        print("Environmental Summary:")
        env_summary = completion_report['environmental_summary']
        print(f"  Time: {env_summary['time']}")
        print(f"  Battery Level: {env_summary['battery_level']:.1f}%")
        print(f"  O2 Level: {env_summary['o2_level']:.1f}%")
        print(f"  Temperature: {env_summary['temperature']:.1f}°C")
        print(f"  Solar Radiation: {env_summary['solar_radiation']:.1f} W/m²")
        print(f"  Power Generation: {env_summary['power_generation']:.1f} W")
        print(f"  Power Consumption: {env_summary['power_consumption']:.1f} W")
        print(f"  Goldilocks Zone: {'✓ YES' if env_summary['is_goldilocks_zone'] else '✗ NO'}")
        print(f"  Active Anomalies: {env_summary['active_anomalies']}")
        print("")
        
        # Print MQTT statistics (if enabled)
        if mqtt_client:
            print("MQTT Statistics:")
            mqtt_stats = mqtt_client.get_statistics()
            print(f"  Connected: {mqtt_stats['is_connected']}")
            print(f"  Messages Published: {mqtt_stats['messages_published']}")
            print(f"  Messages Received: {mqtt_stats['messages_received']}")
            print(f"  Connection Errors: {mqtt_stats['connection_errors']}")
            print(f"  Buffered Messages: {mqtt_stats['buffered_messages']}")
            print("")
        
        print("=" * 80)
        print(f"AETHER completed successfully at: {datetime.now().isoformat()}")
        print("=" * 80)
        
        # Cleanup
        if mqtt_client:
            mqtt_client.disconnect()
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("Pipeline interrupted by user")
        return 130
        
    except Exception as e:
        logger.error(f"Pipeline failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
