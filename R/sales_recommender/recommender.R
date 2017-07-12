library(RPostgreSQL)
library(reshape2)
library(data.table)
library(dplyr)
library(lsa)
library(jsonlite)
library(httr)

myCos <- function (x,user_id, y = NULL) 
{
  if (is.matrix(x) && is.null(y)) {
    co = array(0, c(ncol(x), ncol(x)))
    f = colnames(x)
    
    
    dimnames(co) = list(f, f)
    i = grep(paste("^",user_id,"$",sep=""), f)[1]
    for (j in 1:length(f)) {
      co[i, j] = cosine(x[, i], x[, j])
    }
    
    co = co + t(co)
    diag(co) = 1
    
    return(as.matrix(co))
  }
  else if (is.vector(x) && is.vector(y)) {
    return(crossprod(x, y)/sqrt(crossprod(x) * crossprod(y)))
  }
  else if (is.vector(x) && is.matrix(y)) {
    co = vector(mode = "numeric", length = ncol(y))
    names(co) = colnames(y)
    for (i in 1:ncol(y)) {
      co[i] = cosine(x, y[, i])
    }
    return(co)
  }
  else {
    stop("argument mismatch. Either one matrix or two vectors needed as input.")
  }
}

get_sim_users <- function(user_id){
  
  drv <- dbDriver("PostgreSQL")
  con <- dbConnect(drv,host='localhost',port='5432',dbname='vi',user='postgres',password='postgres')
  
  query <- paste("with all_users as (
                 select distinct(user_id) from ch_activity where  deal_id IN ( select distinct(deal_id) from ch_activity where user_id = '",user_id,"') order by user_id
  ),
                 unwanted_deals as (
                 select distinct(deal_id) from ch_activity
                 where user_id = '",user_id,"'
                 ),
                 good_users as(
                 select * from ch_activity
                 where user_id = '",user_id,"' or (user_id in (select * from all_users)
                 and deal_id not in (select * from unwanted_deals))
                 )
                 select deal_id,user_id,sum(quantity) as pocet from ch_activity
                 where user_id in (select user_id from good_users)
                 group by deal_id,user_id
                 order by pocet desc ",sep="")
  rs <- dbSendQuery(con,query)
  activity <- fetch(rs,n=-1)
  
  dbDisconnect(con)
  
  
  if(nrow(activity)==0)
    return(NA)
  simil = as.data.frame(acast(activity, user_id~deal_id, value.var="pocet"))
  simil[is.na(simil)] = 0

 
  
  sim_mat =myCos(t(as.matrix(simil)),user_id)

  sim_users <- sort(sim_mat[as.character(user_id),],decreasing=TRUE)
  
  sim_users <- sim_users[which(names(sim_users) != user_id & sim_users != 0)]
  
  return(sim_users)
}


get_recoms <- function(user_id,sim_users)
{
  num_of_recoms = 10
  deal_ids <- c()
 
  test_deal_ids <- c()
  deal_id_string <- ""
  
  if(length(sim_users) > 0)
  {
   
    must_not_deals = dbQuery(paste("SELECT deal_id FROM train_activity WHERE user_id='",user_id,"'",sep=""))
    must_not_q = '"must_not":{
    "terms":{
    "deal_id":['
    
    for(m in must_not_deals){
      must_not_q = paste(must_not_q,'"',m,'",',sep="")
    }
    must_not_q = paste(substr(must_not_q, 1, nchar(must_not_q)-1),']}},',sep="")

    should_query =  paste('{"size":"20","query": {
                          "bool": {',
                          must_not_q,
                          '"should": [',sep="")
    
    if(length(sim_users) > 1020)
      sim_users <- sim_users[1:1020]
    
    for(u in 1:length(sim_users)){
      tmp = paste('{ "match": {
                  "user_id": {
                  "query":  ',names(sim_users)[u],',
                  "boost": ',sim_users[u],'                        
                  }
    }},')
      should_query = paste(should_query,tmp)
      
}
    should_query <- substr(should_query, 1, nchar(should_query)-1)
    should_query = paste(should_query,']}}}')
    
    write(should_query, file = "D:/Mato/Skola/VI/zadanie2/R/ch_should_query.txt")
    
    names <- c()
    deal_content = content(POST("localhost:9200/zlava_dna3/train_activities/_search",body=should_query))
    
    for(d in deal_content$hits$hits){
      deal_ids <- append(deal_ids,d$`_source`$deal_id)
    }
    deal_ids <- unique(deal_ids)
    
    if(length(deal_ids) > num_of_recoms)
      deal_ids <- deal_ids[1:num_of_recoms]
    #deal_ids <- deal_ids[1:num_of_recoms]
    
    
    
    deal_id_string <- paste(unique(deal_ids),collapse="','",sep="")
    deal_id_string <- paste(deal_id_string,"'",sep="")
    deal_id_string <- paste("'",deal_id_string,sep="")
    
    
    
    for(id in deal_ids){
      deal_full = dbQuery(paste("SELECT * FROM ch_deal_details WHERE id= '",id,"' limit 1",sep=""))
      # if(nrow(deal_full) == 0)
      #  deal_full = dbQuery(paste("SELECT * FROM test_deal_details WHERE id= '",id,"' limit 1",sep=""))
      if(nrow(deal_full) > 0){
        
        
        
        
        # print(deal_full)
        
        elastic_query = paste('{
                              "size":"1",
                              "query":{
                              "bool": {           
                              "should": [
                              { "match": {
                              "title_deal": {
                              "query":  "',deal_full$title_deal,'"
                              
                              }}},{
                              "match":{
                              "deal_id":{
                              "query":"',deal_full$deal_id,'",
                              "boost": "3"
                              
                              }
                              }},{
                              "match":{
                              "title_desc":{
                              "query":"',deal_full$title_desc,'"
                              
                              }
                              }},{
                              "match":{
                              "title_city":{
                              "query":"',deal_full$title_city,'"
                              
                              }
                              }},{
                              "match":{
                              "partner_id":{
                              "query":"',deal_full$partner_id,'"
                              
                              }
                              }}
                              
                              ],
                              "must":
                              
                              
                              {"range":
                              {
                              "detail.coupon_end_time":{
                              "gte": "1412164800"
                              }
                              
                              }}
                              
                              }}
                              
      }',sep="")
        
        write(elastic_query, file = "D:/Mato/Skola/VI/zadanie2/R/ch_elastic_query.txt")
        
        returned_deals = content(POST("localhost:9200/zlava_dna3/train_deals_nested/_search",body=elastic_query))
        test_deal_ids <- append(test_deal_ids,returned_deals$hits$hits[[1]]$`_source`$deal_id)
        # print(returned_deals$hits$hits[[1]]$`_source`$deal_id)
        
    }
      
      }
    if(length(test_deal_ids) > 0){
      deal_ids <- test_deal_ids
      
    }
    
    
    }
  
  
  if(length(deal_ids) < num_of_recoms)
  {
    if(length(deal_id_string) <= 1)
      deal_id_string <- "''"
    num_deals_needed <- num_of_recoms - length(deal_ids)
    print(paste("NEEDED:",num_deals_needed))
    dni_dozadu = 7
    top_sold_from = as.Date(as.POSIXct(strtoi("1412164800"), origin="1970-01-01")) - dni_dozadu
    top_sold_from = as.character(as.numeric(as.POSIXct(top_sold_from)))
    top_sold_q = paste("with train as(
                       SELECT deal_id FROM ch_activity
                       WHERE deal_id not in  (",deal_id_string,") AND
                       create_time >='",top_sold_from,"'
                       
    )
                       SELECT deal_id,count(*) as pocet from train
                       group by deal_id
                       order by pocet DESC 
                       LIMIT ",num_deals_needed,sep="")
    
    write(top_sold_q, file = "D:/Mato/Skola/VI/zadanie2/R/ch_psql_query.txt")
    
    new_deals <- dbQuery(top_sold_q)
    
    deal_ids <-c(deal_ids,new_deals$deal_id)
    
  }
  
  return(deal_ids)
  }

get_precision <- function(real_ids,recom_ids){
  
  
  real_ids <- real_ids
  k = min(length(recom_ids),length(real_ids))
  if(k==0)
    return(0)

  precision = length(intersect(real_ids,recom_ids))/k

  
}

myMatch <- function(real,recoms){
  indices <- c()
  for(e in real){
    indices <- append(indices,which(e==recoms))
  }
  return(sort(indices))
}

dbQuery <- function(query){
  drv <- dbDriver("PostgreSQL")
  con <- dbConnect(drv,host='localhost',port='5432',dbname='vi',user='postgres',password='postgres')
  
  rs <- dbSendQuery(con,query)
  data <- fetch(rs,n=-1)
  dbDisconnect(con)
  return(data) 
}

pocet_userov = 1000000
#MAX=53642

test_users <- read.csv("D:/Mato/Skola/VI/zadanie2/R/user_id.csv", header = FALSE, sep = ",")
#print(test_users[,1])
#exit
#test_users <- c("144645")
i = 1
user_count = length(test_users[,1])

final_output = ""
recoms_output <- c()


  for(user in test_users[,1]){
   
    similar_users <- get_sim_users(user)
    recoms <- get_recoms(user,similar_users)   
    write.table(paste(user,",",recoms,sep=""), file="D:/Mato/Skola/VI/zadanie2/R/ch_recoms.csv", 
                row.names=FALSE, col.names=FALSE, sep=",",quote=FALSE,append=TRUE)
    print(paste(i,"/",user_count,sep=""))
    i = i+1

  exit
  }


 
  


