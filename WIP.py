# Sample API for all execution shit:

Reportable(object):


    def update_context_before():
        pass
    def update_context_after(self, context, ):
        pass

    def setup(self, context, *args, **kwargs):
        print("")
    
    # Execution object might be a curl handle, a test/benchmark, whatever
    # For benchmarks, an execution object is a sub-reportable with lifecycle for each request

    def real_execution():hr
        self.update_context()
        self.apply_templating()  # Currently what we use to generate a templated object
        self.initalize_report()
        self.initialize_execution(self, execution_object, templated_result)
        self.pre_execution(self, execution_object) # for delays, etc
        self.run_execution(self, execution_object)
        self.post_execution(self, execution_object)  # for post-request cleanup
        self.analyze_execution(self, execution_object, report_object)
        self.analyze_report(self, report_object)
        self.update_context_after()



REPORTABLE METHOD:
    runme:
        - update_context_before
        - initalize_reporting/states -> return obj for report 
        
        - create_exection(self, options) -> returns object specific to impl
        - run_exection -> curl.perform or benchmark loop
        - analyze_execution -> does collection of data from execution

        - update_context_after(request, execution_info)
        - generate_report/

