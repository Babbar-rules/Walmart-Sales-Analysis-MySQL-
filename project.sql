use project;

# Need to change name foramt of some columns as they contain spaces.
ALTER TABLE walmartsales
CHANGE COLUMN `Customer type` Customer_type VARCHAR(255),
CHANGE COLUMN `Product line` Product_line VARCHAR(255),
CHANGE COLUMN `Unit price` Unit_price double,
CHANGE COLUMN `Tax 5%` Tax_5_percent double,
CHANGE COLUMN `gross margin percentage` gross_margin_percentage double,
CHANGE COLUMN `gross income` gross_income double,
CHANGE COLUMN `Customer ID` Customer_ID int,
CHANGE COLUMN `Invoice ID` Invoice_ID text;


# task 1
select Branch, YearMonth, TotalSales, 
       ((TotalSales - PrevMonthSales) / PrevMonthSales)*100 as SalesGrowth_percent
from (
    select Branch, 
           date_format(str_to_date(Date, '%d-%m-%Y'), '%Y-%m') as YearMonth,
           sum(Total) as TotalSales,
           lag(sum(Total)) OVER (partition by Branch order by date_format(str_to_date(Date, '%d-%m-%Y'), '%Y-%m')) as PrevMonthSales
    from walmartsales
    group by Branch, YearMonth
) as SalesData
where PrevMonthSales is not null 
order by SalesGrowth_percent desc
limit 1;


#task 2
select Branch, Product_line,  (total_cogs - total_gross_income) as profit
from(
     select Branch,
			Product_line,
     sum(cogs) as total_cogs,
     sum(gross_income) as total_gross_income,
     rank() over (partition by Branch order by (total_cogs - total_gross_income) desc ) as ranks
	from walmartsales
    group by Branch,Product_line)
    as product_detail
    where ranks =1;
    
#task 3
select Customer_ID,
       sum(Total) as Total_sales,
       avg(Total) as Avg_sales,
       case
           when sum(Total) > 25000 then "High"
           when sum(Total) > 20000 then "Medium"
           else "low"
		end as Spendingtier
	
from walmartsales
group by Customer_ID
order by Customer_ID;

#task 4
select * from walmartsales as sales
join (
	 select Product_line,  avg(Total) as avg_total, stddev(Total) as std_dev
     from walmartsales
     group by Product_line
     ) 
as avg_data
on sales.Product_line = avg_data.Product_line
where sales.Total > avg_data.avg_total + 2 * avg_data.std_dev
or sales.Total < avg_data.avg_total - 2 * avg_data.std_dev;

#task 5
select City, Payment, payment_count
from(
select City,
	   Payment,
       count(Payment) as payment_count,
       rank() over (partition by City order by count(Payment) desc) as ranks
from walmartsales
group by City, Payment) 
as rankedpayments
where ranks =1;


#task 6
select Gender,
    month(str_to_date(Date, '%d-%m-%Y')) as month_number,
    sum(Total) as Total_sales
from walmartsales
group by Gender, month_number
order by month_number,Total_sales desc;


#task 7
select Customer_type, Product_line, count(Product_line) as count_product
from walmartsales
group by Customer_type, Product_line
order by count_product desc
limit 3;

#task 8
select distinct w1.customer_type, w1.city, count(distinct w1.customer_id) as Repeat_customer_count
from walmartsales w1
join walmartsales w2 
on w1.customer_id = w2.customer_id
and abs(datediff(str_to_date(w1.date, '%d-%m-%Y'), str_to_date(w2.date, '%d-%m-%Y'))) between 1 and 30
group by w1.customer_type, w1.city
order by w1.customer_type, w1.city;

#task 9
select Customer_ID, sum(Total) as total_sales
from walmartsales
group by Customer_ID
order by total_sales desc
limit 5;

#task 10
select 
     dayname(str_to_date(Date, '%d-%m-%Y')) as day_name,
     sum(Total) as total_sales
from walmartsales
group by day_name
order by total_sales desc;

