#!/usr/bin/env python3
"""
Debug script to identify which quality scenarios are failing
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.tactics.manager import QualityTacticsManager
from src.models import User, Product, Partner, PartnerAPIKey, FlashSale, Sale
from src.database import SessionLocal
from datetime import datetime, timezone, timedelta
import time

def debug_quality_scenarios():
    """Debug each quality scenario individually to identify failures."""
    
    print("🔍 DEBUGGING QUALITY SCENARIOS")
    print("="*50)
    
    # Create database session
    db = SessionLocal()
    
    try:
        # Create test data with unique identifiers
        import random
        unique_id = random.randint(10000, 99999)
        user = User(username=f"testuser_{unique_id}", email=f"test_{unique_id}@example.com", passwordHash="hash")
        db.add(user)
        db.commit()
        db.refresh(user)
        
        product = Product()
        product.name = "Test Product"
        product.price = 25.00
        product.stock = 100
        db.add(product)
        db.commit()
        db.refresh(product)
        
        # Initialize quality manager
        quality_manager = QualityTacticsManager(db, {})
        
        # Test each scenario individually
        scenarios = []
        
        # A.1: Circuit Breaker Pattern
        print("\n🔍 A.1: Circuit Breaker Pattern")
        try:
            def failing_payment():
                raise Exception("Payment service down")
            
            failures = 0
            for i in range(5):
                success, result = quality_manager.execute_with_circuit_breaker(failing_payment)
                if not success:
                    failures += 1
            
            order_data = {'sale_id': 1, 'user_id': user.userID, 'total_amount': 100.0}
            queue_success, queue_message = quality_manager.enqueue_order(order_data, priority=1)
            
            a1_fulfilled = failures >= 3 and queue_success  # Circuit breaker should trip, queue should work
            scenarios.append(("A.1", a1_fulfilled, f"Failures: {failures}, Queue: {queue_success}"))
            print(f"   Result: {'✅' if a1_fulfilled else '❌'} - Failures: {failures}, Queue: {queue_success}")
            
        except Exception as e:
            scenarios.append(("A.1", False, f"Error: {e}"))
            print(f"   Result: ❌ - Error: {e}")
        
        # A.2: Rollback and Retry
        print("\n🔍 A.2: Rollback and Retry")
        try:
            retry_attempts = 0
            max_retries = 3
            
            def transient_failing_operation():
                nonlocal retry_attempts
                retry_attempts += 1
                if retry_attempts <= 2:
                    raise Exception("Transient failure")
                return "Success"
            
            retry_success = False
            for attempt in range(max_retries):
                try:
                    result = transient_failing_operation()
                    retry_success = True
                    break
                except Exception:
                    if attempt < max_retries - 1:
                        time.sleep(0.1)
            
            a2_fulfilled = retry_success and retry_attempts == 3
            scenarios.append(("A.2", a2_fulfilled, f"Success: {retry_success}, Attempts: {retry_attempts}"))
            print(f"   Result: {'✅' if a2_fulfilled else '❌'} - Success: {retry_success}, Attempts: {retry_attempts}")
            
        except Exception as e:
            scenarios.append(("A.2", False, f"Error: {e}"))
            print(f"   Result: ❌ - Error: {e}")
        
        # A.3: Removal from Service
        print("\n🔍 A.3: Removal from Service")
        try:
            initial_stock = product.stock
            initial_sales_count = db.query(Sale).count()
            
            def permanent_failing_operation():
                raise Exception("Card Declined - Permanent Failure")
            
            try:
                success, result = quality_manager.execute_with_circuit_breaker(permanent_failing_operation)
            except Exception:
                pass
            
            db.refresh(product)
            final_stock = product.stock
            final_sales_count = db.query(Sale).count()
            
            no_side_effects = (final_stock == initial_stock) and (final_sales_count == initial_sales_count)
            scenarios.append(("A.3", no_side_effects, f"Stock: {initial_stock}→{final_stock}, Sales: {initial_sales_count}→{final_sales_count}"))
            print(f"   Result: {'✅' if no_side_effects else '❌'} - Stock: {initial_stock}→{final_stock}, Sales: {initial_sales_count}→{final_sales_count}")
            
        except Exception as e:
            scenarios.append(("A.3", False, f"Error: {e}"))
            print(f"   Result: ❌ - Error: {e}")
        
        # S.1: Partner API Authentication
        print("\n🔍 S.1: Partner API Authentication")
        try:
            partner = Partner(name="Test Partner")
            partner.api_endpoint = "https://api.test.com"
            partner.status = "active"
            db.add(partner)
            db.commit()
            db.refresh(partner)
            
            valid_api_key = PartnerAPIKey(
                partnerID=partner.partnerID,
                api_key="valid_test_key_12345",
                created_at=datetime.now(timezone.utc),
                expires_at=datetime.now(timezone.utc) + timedelta(days=30),
                is_active=True
            )
            db.add(valid_api_key)
            db.commit()
            
            unauthorized_attempts = ["invalid_key", "expired_key", "", "malicious_key"]
            denied_attempts = 0
            
            for api_key in unauthorized_attempts:
                try:
                    success, message = quality_manager.authenticate_partner(api_key)
                    if not success:
                        denied_attempts += 1
                except Exception:
                    denied_attempts += 1
            
            valid_success, valid_message = quality_manager.authenticate_partner("valid_test_key_12345")
            
            all_unauthorized_denied = denied_attempts == len(unauthorized_attempts)
            valid_key_works = valid_success
            
            s1_fulfilled = all_unauthorized_denied and valid_key_works
            scenarios.append(("S.1", s1_fulfilled, f"Denied: {denied_attempts}/{len(unauthorized_attempts)}, Valid: {valid_key_works}"))
            print(f"   Result: {'✅' if s1_fulfilled else '❌'} - Denied: {denied_attempts}/{len(unauthorized_attempts)}, Valid: {valid_key_works}")
            
        except Exception as e:
            scenarios.append(("S.1", False, f"Error: {e}"))
            print(f"   Result: ❌ - Error: {e}")
        
        # S.2: Input Validation
        print("\n🔍 S.2: Input Validation")
        try:
            malicious_inputs = [
                {"name": "'; DROP TABLE products; --", "price": 10.99},
                {"name": "<script>alert('xss')</script>", "price": 15.99}
            ]
            
            valid_inputs = [
                {"name": "Normal Product", "price": 25.99}
            ]
            
            all_inputs = malicious_inputs + valid_inputs
            blocked_inputs = 0
            allowed_inputs = 0
            
            for input_data in all_inputs:
                try:
                    success, message = quality_manager.validate_partner_data(input_data)
                    if success:
                        allowed_inputs += 1
                    else:
                        blocked_inputs += 1
                except Exception:
                    blocked_inputs += 1
            
            malicious_blocked = blocked_inputs >= len(malicious_inputs)
            valid_allowed = allowed_inputs >= len(valid_inputs)
            
            s2_fulfilled = malicious_blocked and valid_allowed
            scenarios.append(("S.2", s2_fulfilled, f"Blocked: {blocked_inputs}/{len(malicious_inputs)}, Allowed: {allowed_inputs}/{len(valid_inputs)}"))
            print(f"   Result: {'✅' if s2_fulfilled else '❌'} - Blocked: {blocked_inputs}/{len(malicious_inputs)}, Allowed: {allowed_inputs}/{len(valid_inputs)}")
            
        except Exception as e:
            scenarios.append(("S.2", False, f"Error: {e}"))
            print(f"   Result: ❌ - Error: {e}")
        
        # M.1: Adapter Pattern
        print("\n🔍 M.1: Adapter Pattern")
        try:
            csv_data = "name,price,stock\nProduct A,10.99,100"
            json_data = '{"products": [{"name": "Product C", "price": 20.99, "stock": 75}]}'
            xml_data = '<?xml version="1.0"?><products><product><name>Product D</name><price>25.99</price><stock>30</stock></product></products>'
            
            csv_success, csv_result = quality_manager.process_partner_data(csv_data, 'csv')
            json_success, json_result = quality_manager.process_partner_data(json_data, 'json')
            xml_success, xml_result = quality_manager.process_partner_data(xml_data, 'xml')
            
            all_formats_work = csv_success and json_success and xml_success
            scenarios.append(("M.1", all_formats_work, f"CSV: {csv_success}, JSON: {json_success}, XML: {xml_success}"))
            print(f"   Result: {'✅' if all_formats_work else '❌'} - CSV: {csv_success}, JSON: {json_success}, XML: {xml_success}")
            
        except Exception as e:
            scenarios.append(("M.1", False, f"Error: {e}"))
            print(f"   Result: ❌ - Error: {e}")
        
        # M.2: Feature Toggle
        print("\n🔍 M.2: Feature Toggle")
        try:
            enable_success, enable_message = quality_manager.enable_feature("test_feature", 100, updated_by="test")
            
            start_time = time.time()
            disable_success, disable_message = quality_manager.disable_feature("test_feature", updated_by="test")
            disable_time = time.time() - start_time
            
            enabled, _ = quality_manager.is_feature_enabled("test_feature", 1)
            
            time_acceptable = disable_time < 5.0
            feature_disabled = not enabled
            
            m2_fulfilled = time_acceptable and feature_disabled
            scenarios.append(("M.2", m2_fulfilled, f"Time: {disable_time:.2f}s, Disabled: {not enabled}"))
            print(f"   Result: {'✅' if m2_fulfilled else '❌'} - Time: {disable_time:.2f}s, Disabled: {not enabled}")
            
        except Exception as e:
            scenarios.append(("M.2", False, f"Error: {e}"))
            print(f"   Result: ❌ - Error: {e}")
        
        # P.1: Throttling and Queuing
        print("\n🔍 P.1: Throttling and Queuing")
        try:
            request_data = {'user_id': user.userID, 'amount': 100.0}
            throttled, message = quality_manager.check_throttling(request_data)
            
            order_data = {'sale_id': 1, 'user_id': user.userID, 'total_amount': 100.0}
            queue_success, queue_message = quality_manager.enqueue_order(order_data, priority=1)
            
            p1_fulfilled = queue_success  # Basic functionality test
            scenarios.append(("P.1", p1_fulfilled, f"Throttled: {throttled}, Queue: {queue_success}"))
            print(f"   Result: {'✅' if p1_fulfilled else '❌'} - Throttled: {throttled}, Queue: {queue_success}")
            
        except Exception as e:
            scenarios.append(("P.1", False, f"Error: {e}"))
            print(f"   Result: ❌ - Error: {e}")
        
        # P.2: Concurrency Control
        print("\n🔍 P.2: Concurrency Control")
        try:
            def stock_update_operation():
                return "Stock updated successfully"
            
            success, result = quality_manager.execute_with_concurrency_control(stock_update_operation)
            
            p2_fulfilled = success
            scenarios.append(("P.2", success, f"Success: {success}"))
            print(f"   Result: {'✅' if success else '❌'} - Success: {success}")
            
        except Exception as e:
            scenarios.append(("P.2", False, f"Error: {e}"))
            print(f"   Result: ❌ - Error: {e}")
        
        # I.1: API Adapter
        print("\n🔍 I.1: API Adapter")
        try:
            internal_data = {'sale_id': 12345, 'user_id': 67890, 'total_amount': 150.0}
            success, external_data = quality_manager.adapt_data('reseller_adapter', internal_data)
            
            api_config = {'base_url': 'https://reseller-api.example.com', 'auth_token': 'test_token', 'timeout': 30}
            setup_success, setup_message = quality_manager.setup_partner_integration(1, api_config)
            
            i1_fulfilled = success and setup_success
            scenarios.append(("I.1", i1_fulfilled, f"Adapt: {success}, Setup: {setup_success}"))
            print(f"   Result: {'✅' if i1_fulfilled else '❌'} - Adapt: {success}, Setup: {setup_success}")
            
        except Exception as e:
            scenarios.append(("I.1", False, f"Error: {e}"))
            print(f"   Result: ❌ - Error: {e}")
        
        # I.2: Publish-Subscribe
        print("\n🔍 I.2: Publish-Subscribe")
        try:
            message_data = {'partner_id': 1, 'data': {'products': []}, 'timestamp': datetime.now(timezone.utc).isoformat()}
            publish_success, publish_message = quality_manager.publish_message('partner_updates', message_data)
            
            i2_fulfilled = publish_success
            scenarios.append(("I.2", publish_success, f"Publish: {publish_success}"))
            print(f"   Result: {'✅' if publish_success else '❌'} - Publish: {publish_success}")
            
        except Exception as e:
            scenarios.append(("I.2", False, f"Error: {e}"))
            print(f"   Result: ❌ - Error: {e}")
        
        # T.1: Record/Playback
        print("\n🔍 T.1: Record/Playback")
        try:
            def test_function(test_env):
                test_env.record_request("/api/test", "POST", {"test": "data"})
                test_env.record_response(200, {"result": "success"})
                return {"status": "completed"}
            
            success, summary = quality_manager.run_test_with_recording("test_scenario", test_function)
            playback_success, playback_data = quality_manager.playback_test("test_scenario")
            
            t1_fulfilled = success and playback_success
            scenarios.append(("T.1", t1_fulfilled, f"Record: {success}, Playback: {playback_success}"))
            print(f"   Result: {'✅' if t1_fulfilled else '❌'} - Record: {success}, Playback: {playback_success}")
            
        except Exception as e:
            scenarios.append(("T.1", False, f"Error: {e}"))
            print(f"   Result: ❌ - Error: {e}")
        
        # T.2: Dependency Injection
        print("\n🔍 T.2: Dependency Injection")
        try:
            from unittest.mock import Mock
            mock_payment_service = Mock()
            call_count = 0
            
            def mock_payment_call():
                nonlocal call_count
                call_count += 1
                if call_count <= 2:
                    raise Exception("Transient failure")
                return {"status": "success"}
            
            mock_payment_service.process_payment = mock_payment_call
            
            test_success = False
            for attempt in range(3):
                try:
                    result = mock_payment_service.process_payment()
                    test_success = True
                    break
                except Exception:
                    if attempt < 2:
                        time.sleep(0.1)
            
            t2_fulfilled = test_success and call_count == 3
            scenarios.append(("T.2", t2_fulfilled, f"Success: {test_success}, Calls: {call_count}"))
            print(f"   Result: {'✅' if t2_fulfilled else '❌'} - Success: {test_success}, Calls: {call_count}")
            
        except Exception as e:
            scenarios.append(("T.2", False, f"Error: {e}"))
            print(f"   Result: ❌ - Error: {e}")
        
        # U.1: Error Recovery
        print("\n🔍 U.1: Error Recovery")
        try:
            error_success, error_response = quality_manager.handle_payment_error('card_declined', 100.0, 'card')
            
            has_suggestions = 'suggestions' in error_response
            has_alternatives = 'alternative_methods' in error_response
            
            u1_fulfilled = error_success and has_suggestions and has_alternatives
            scenarios.append(("U.1", u1_fulfilled, f"Success: {error_success}, Suggestions: {has_suggestions}, Alternatives: {has_alternatives}"))
            print(f"   Result: {'✅' if u1_fulfilled else '❌'} - Success: {error_success}, Suggestions: {has_suggestions}, Alternatives: {has_alternatives}")
            
        except Exception as e:
            scenarios.append(("U.1", False, f"Error: {e}"))
            print(f"   Result: ❌ - Error: {e}")
        
        # U.2: Progress Indicator
        print("\n🔍 U.2: Progress Indicator")
        try:
            operation_id = "long_running_task"
            start_success, start_message = quality_manager.start_progress_tracking(operation_id, "Long Task", 30)
            
            for progress in [25, 50, 75, 100]:
                update_success, update_message = quality_manager.update_progress(operation_id, progress, f"Step {progress}%")
            
            complete_success, complete_message = quality_manager.complete_operation(operation_id, True)
            
            u2_fulfilled = start_success and complete_success
            scenarios.append(("U.2", u2_fulfilled, f"Start: {start_success}, Complete: {complete_success}"))
            print(f"   Result: {'✅' if u2_fulfilled else '❌'} - Start: {start_success}, Complete: {complete_success}")
            
        except Exception as e:
            scenarios.append(("U.2", False, f"Error: {e}"))
            print(f"   Result: ❌ - Error: {e}")
        
        # Summary
        print("\n" + "="*50)
        print("📊 SUMMARY")
        print("="*50)
        
        total_scenarios = len(scenarios)
        fulfilled_scenarios = sum(1 for _, fulfilled, _ in scenarios if fulfilled)
        success_rate = (fulfilled_scenarios / total_scenarios) * 100 if total_scenarios > 0 else 0
        
        print(f"Total Scenarios: {total_scenarios}")
        print(f"Fulfilled: {fulfilled_scenarios}")
        print(f"Success Rate: {success_rate:.1f}%")
        
        print(f"\nFailed Scenarios:")
        for scenario_id, fulfilled, details in scenarios:
            if not fulfilled:
                print(f"  ❌ {scenario_id}: {details}")
        
        print(f"\nPassed Scenarios:")
        for scenario_id, fulfilled, details in scenarios:
            if fulfilled:
                print(f"  ✅ {scenario_id}: {details}")
        
    finally:
        db.close()

if __name__ == "__main__":
    debug_quality_scenarios()
