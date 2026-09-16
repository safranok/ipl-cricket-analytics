DROP VIEW IF EXISTS v_ball;  -- so the file can be run twice  
CREATE VIEW v_ball AS  
SELECT d.*,                  -- keep every original column  
   
       CASE WHEN d.over_number <= 5  THEN 'Powerplay'  
            WHEN d.over_number <= 14 THEN 'Middle'  
            ELSE 'Death' END AS phase,  
       -- ^ label each ball with its part of the innings  
   
       CASE WHEN d.is_wide_ball = 0 AND d.is_no_ball = 0  
            THEN 1 ELSE 0 END AS is_legal,  
       -- ^ 1 if the ball counted towards the over, 0 if it was re-bowled  
   
       d.total_runs - d.bye_runs - d.leg_bye_runs  
                    - d.penalty_runs AS bowler_runs,  
       -- ^ runs that were actually the bowler's fault  
   
       CASE WHEN d.is_wicket = 1 AND d.wicket_kind NOT IN  
            ('run out','retired hurt','retired out',  
             'obstructing the field')  
            THEN 1 ELSE 0 END AS bowler_wicket  
       -- ^ 1 only if the bowler gets the credit for the wicket  
   
FROM   deliveries d  
WHERE  d.is_super_over = 0;  -- drop the 175 tie-breaker balls